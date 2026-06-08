from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import MENU_BUTTONS, cancel_keyboard, main_menu_keyboard, settings_keyboard
from src.bot.states import BackupRestore, SetupDuress, SetupPin
from src.crypto import encrypt_seed, hash_password, verify_password
from src.database.repository import Repository
from src.security.audit import AuditLogger
from src.security.backup import backup_item_to_bytes, decrypt_backup_file
from src.security.password_strength import check_password_strength
from src.security.session import SessionManager
from src.security.validators import validate_seed_phrase, validate_wallet_name

router = Router()


@router.callback_query(F.data == "audit_log")
async def show_audit(callback: CallbackQuery, repo: Repository, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Заблокирован", show_alert=True)
        return
    entries = await repo.get_audit_log(callback.from_user.id, 15)
    if not entries:
        await callback.message.edit_text("📜 Журнал пуст.")
    else:
        lines = []
        for e in reversed(entries):
            t = e.created_at.strftime("%d.%m %H:%M")
            d = f" — {e.details}" if e.details else ""
            lines.append(f"• {t}: {e.action}{d}")
        await callback.message.edit_text(
            "📜 <b>Журнал активности</b>\n\n" + "\n".join(lines),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "setup_pin")
async def setup_pin_start(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if session.is_duress_mode(callback.from_user.id):
        await callback.answer("Недоступно в duress-режиме", show_alert=True)
        return
    await state.set_state(SetupPin.pin)
    await callback.message.answer("🔢 Введите 6-значный PIN:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(SetupPin.pin, F.text == "❌ Отмена")
@router.message(SetupPin.pin_confirm, F.text == "❌ Отмена")
async def cancel_pin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_keyboard())


@router.message(SetupPin.pin, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def process_pin(message: Message, state: FSMContext) -> None:
    pin = (message.text or "").strip()
    await message.delete()
    if not pin.isdigit() or len(pin) != 6:
        await message.answer("PIN: 6 цифр.")
        return
    await state.update_data(pin=pin)
    await state.set_state(SetupPin.pin_confirm)
    await message.answer("🔁 Повторите PIN:", reply_markup=cancel_keyboard())


@router.message(SetupPin.pin_confirm, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def confirm_pin(
    message: Message, state: FSMContext, repo: Repository, audit: AuditLogger,
) -> None:
    pin = (message.text or "").strip()
    await message.delete()
    data = await state.get_data()
    if pin != data.get("pin"):
        await message.answer("❌ PIN не совпадает.")
        await state.clear()
        return
    tid = message.from_user.id
    await repo.update_pin(tid, hash_password(pin), True)
    await audit.log(tid, "pin_enabled")
    await state.clear()
    await message.answer("✅ PIN включён.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "setup_duress")
async def setup_duress_start(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if session.is_duress_mode(callback.from_user.id):
        await callback.answer("Выйдите из duress-режима", show_alert=True)
        return
    await state.set_state(SetupDuress.password)
    await callback.message.answer(
        "🎭 <b>Duress-пароль</b>\n\n"
        "При вводе этого пароля откроются только <b>ложные</b> кошельки.\n"
        "Введите duress-пароль:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SetupDuress.password, F.text == "❌ Отмена")
@router.message(SetupDuress.password_confirm, F.text == "❌ Отмена")
async def cancel_duress(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_keyboard())


@router.message(SetupDuress.password, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def duress_password(message: Message, state: FSMContext, repo: Repository) -> None:
    password = message.text or ""
    await message.delete()
    user = await repo.get_user(message.from_user.id)
    if user and verify_password(user.password_hash, password):
        await message.answer("❌ Duress-пароль не должен совпадать с основным.")
        return
    if not check_password_strength(password).acceptable:
        await message.answer("❌ Слишком слабый пароль.")
        return
    await state.update_data(duress_password=password)
    await state.set_state(SetupDuress.password_confirm)
    await message.answer("🔁 Повторите duress-пароль:", reply_markup=cancel_keyboard())


@router.message(SetupDuress.password_confirm, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def duress_confirm(
    message: Message, state: FSMContext, repo: Repository, audit: AuditLogger,
) -> None:
    password = message.text or ""
    await message.delete()
    data = await state.get_data()
    if password != data.get("duress_password"):
        await message.answer("❌ Не совпадает.")
        await state.clear()
        return
    tid = message.from_user.id
    await repo.update_duress(tid, hash_password(password))
    await audit.log(tid, "duress_enabled")
    await state.clear()
    await message.answer(
        "✅ Duress-пароль установлен.\n"
        "Добавьте ложные кошельки: ⚙️ → 🎭 Ложные кошельки",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "decoy_wallets")
async def decoy_info(callback: CallbackQuery, session: SessionManager, repo: Repository) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Заблокирован", show_alert=True)
        return
    if session.is_duress_mode(callback.from_user.id):
        await callback.answer("Выйдите из duress-режима", show_alert=True)
        return
    count = await repo.count_wallets(callback.from_user.id, decoy=True)
    await callback.message.answer(
        f"🎭 Ложных кошельков: {count}\n"
        "Для добавления: /lock → разблокируйте duress-паролём → ➕ Добавить кошелёк",
    )
    await callback.answer()


@router.callback_query(F.data == "restore")
async def restore_start(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Заблокирован", show_alert=True)
        return
    if session.is_duress_mode(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return
    await state.set_state(BackupRestore.waiting_file)
    await callback.message.answer(
        "📥 Отправьте файл <code>.snx</code> бэкапа.\n"
        "Затем потребуется пароль.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BackupRestore.waiting_file, F.document)
async def restore_file(
    message: Message, state: FSMContext, repo: Repository, session: SessionManager,
) -> None:
    doc = message.document
    if not doc.file_name or not doc.file_name.endswith(".snx"):
        await message.answer("Нужен файл .snx")
        return
    file = await message.bot.download(doc)
    await state.update_data(backup_bytes=file.read())
    await state.set_state(BackupRestore.password)
    await message.answer("🔐 Пароль для расшифровки бэкапа:", reply_markup=cancel_keyboard())


@router.message(BackupRestore.password, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def restore_password(
    message: Message, state: FSMContext, repo: Repository, session: SessionManager, audit: AuditLogger,
) -> None:
    password = message.text or ""
    await message.delete()
    data = await state.get_data()
    user = await repo.get_user(message.from_user.id)
    if user is None:
        await state.clear()
        return
    try:
        payload = decrypt_backup_file(data["backup_bytes"], password, user.salt)
    except Exception:
        await message.answer("❌ Неверный пароль или повреждённый файл.")
        await state.clear()
        return

    items = []
    for w in payload.get("wallets", []):
        items.append(backup_item_to_bytes(w))

    count = await repo.import_wallets(message.from_user.id, items)
    await audit.log(message.from_user.id, "restore", f"{count} кошельков")
    await state.clear()
    await message.answer(
        f"✅ Восстановлено: {count} кошельков.",
        reply_markup=main_menu_keyboard(),
    )
