import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.helpers import is_active, log_action, reply_locked, use_decoy
from src.bot.keyboards import (
    MENU_BUTTONS,
    cancel_keyboard,
    main_menu_keyboard,
    wallet_actions_keyboard,
    wallets_list_keyboard,
)
from src.bot.states import AddWallet, EditWallet, SearchWallet
from src.config import get_settings
from src.crypto import decrypt_seed, encrypt_seed
from src.database.repository import Repository
from src.security.audit import AuditLogger
from src.security.session import SessionManager
from src.security.validators import validate_seed_phrase, validate_wallet_name

router = Router()
logger = logging.getLogger(__name__)


async def start_search(message: Message, state: FSMContext, session: SessionManager) -> None:
    if not is_active(session, message.from_user.id):
        await reply_locked(message)
        return
    await state.set_state(SearchWallet.query)
    await message.answer("🔍 Введите часть названия:", reply_markup=cancel_keyboard())


@router.message(SearchWallet.query, F.text == "❌ Отмена")
async def cancel_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_keyboard())


@router.message(SearchWallet.query)
async def process_search(
    message: Message, state: FSMContext, repo: Repository, session: SessionManager,
) -> None:
    query = (message.text or "").strip()
    await state.clear()
    decoy = use_decoy(session, message.from_user.id)
    wallets = await repo.get_wallets(message.from_user.id, decoy=decoy, search=query)
    if not wallets:
        await message.answer(f"Ничего не найдено по «{query}».")
        return
    await message.answer(
        f"🔍 Найдено {len(wallets)}:",
        reply_markup=wallets_list_keyboard(wallets),
    )


@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery, repo: Repository, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Заблокирован", show_alert=True)
        return
    decoy = use_decoy(session, callback.from_user.id)
    wallets = await repo.get_wallets(callback.from_user.id, decoy=decoy)
    await callback.message.edit_text(
        f"📋 <b>Кошельки</b> ({len(wallets)}):",
        reply_markup=wallets_list_keyboard(wallets),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("wallet:"))
async def show_wallet(callback: CallbackQuery, repo: Repository, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Заблокирован", show_alert=True)
        return
    decoy = use_decoy(session, callback.from_user.id)
    wallet_id = int(callback.data.split(":")[1])
    wallet = await repo.get_wallet(wallet_id, callback.from_user.id, decoy=decoy)
    if wallet is None:
        await callback.answer("Не найден", show_alert=True)
        return
    note_hint = " 📝" if wallet.encrypted_note else ""
    await callback.message.edit_text(
        f"👛 <b>{wallet.name}</b>{note_hint}\n"
        f"📅 {wallet.created_at.strftime('%d.%m.%Y')}",
        reply_markup=wallet_actions_keyboard(wallet.id),
        parse_mode="HTML",
    )
    await callback.answer()


async def start_add_wallet(
    message: Message, state: FSMContext, session: SessionManager, repo: Repository,
) -> None:
    if not is_active(session, message.from_user.id):
        await reply_locked(message)
        return
    settings = get_settings()
    decoy = use_decoy(session, message.from_user.id)
    count = await repo.count_wallets(message.from_user.id, decoy=decoy)
    if count >= settings.max_wallets_per_user:
        await message.answer(f"Лимит: {settings.max_wallets_per_user} кошельков.")
        return
    await state.update_data(decoy=decoy)
    await state.set_state(AddWallet.name)
    label = "ложный" if decoy else "кошелёк"
    await message.answer(f"📝 Название {label}а:", reply_markup=cancel_keyboard())


@router.message(AddWallet.name, F.text == "❌ Отмена")
@router.message(AddWallet.note, F.text == "❌ Отмена")
@router.message(AddWallet.seed, F.text == "❌ Отмена")
async def cancel_add(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_keyboard())


@router.message(AddWallet.name, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def process_name(message: Message, state: FSMContext) -> None:
    result = validate_wallet_name(message.text or "")
    if not result.valid:
        await message.answer(f"❌ {result.error}")
        return
    await state.update_data(wallet_name=message.text.strip())
    await state.set_state(AddWallet.note)
    await message.answer(
        "📝 Заметка (или «-» чтобы пропустить):",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddWallet.note, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def process_note(message: Message, state: FSMContext) -> None:
    note = message.text or ""
    if note.strip() == "-":
        note = ""
    await state.update_data(wallet_note=note.strip())
    await state.set_state(AddWallet.seed)
    await message.answer("🔐 Введите сид-фразу:", reply_markup=cancel_keyboard())


@router.message(AddWallet.seed, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def process_seed(
    message: Message, state: FSMContext, repo: Repository, session: SessionManager, audit: AuditLogger,
) -> None:
    seed = message.text or ""
    await message.delete()
    result = validate_seed_phrase(seed)
    if not result.valid:
        await message.answer(f"❌ {result.error}")
        return

    data = await state.get_data()
    telegram_id = message.from_user.id
    password = session.get_password(telegram_id)
    if password is None:
        await reply_locked(message)
        await state.clear()
        return

    user = await repo.get_user(telegram_id)
    if user is None:
        await state.clear()
        return

    decoy = data.get("decoy", False)
    note_text = data.get("wallet_note", "")
    enc_note = encrypt_seed(note_text, password, user.salt) if note_text else None

    try:
        enc_seed = encrypt_seed(seed.strip().lower(), password, user.salt)
        await repo.add_wallet(
            telegram_id, data["wallet_name"], enc_seed, enc_note, decoy=decoy,
        )
    except Exception:
        logger.exception("encrypt error")
        await message.answer("❌ Ошибка сохранения.")
        await state.clear()
        return

    await log_action(audit, telegram_id, "add_wallet", data["wallet_name"])
    await state.clear()
    await message.answer(
        f"✅ «{data['wallet_name']}» сохранён!",
        reply_markup=main_menu_keyboard(),
    )


# --- Rename / Note edit ---

@router.callback_query(F.data.startswith("rename:"))
async def start_rename(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Заблокирован", show_alert=True)
        return
    wallet_id = int(callback.data.split(":")[1])
    await state.update_data(edit_wallet_id=wallet_id, decoy=use_decoy(session, callback.from_user.id))
    await state.set_state(EditWallet.new_name)
    await callback.message.answer("✏️ Новое название:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("note:"))
async def start_note_edit(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Заблокирован", show_alert=True)
        return
    wallet_id = int(callback.data.split(":")[1])
    await state.update_data(edit_wallet_id=wallet_id, decoy=use_decoy(session, callback.from_user.id))
    await state.set_state(EditWallet.new_note)
    await callback.message.answer(
        "📝 Новая заметка (или «-» чтобы удалить):",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(EditWallet.new_name, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def process_rename(
    message: Message, state: FSMContext, repo: Repository, audit: AuditLogger,
) -> None:
    result = validate_wallet_name(message.text or "")
    if not result.valid:
        await message.answer(f"❌ {result.error}")
        return
    data = await state.get_data()
    ok = await repo.rename_wallet(
        data["edit_wallet_id"], message.from_user.id, message.text.strip(), decoy=data["decoy"],
    )
    await state.clear()
    if ok:
        await audit.log(message.from_user.id, "rename_wallet", message.text.strip())
        await message.answer("✅ Переименовано.", reply_markup=main_menu_keyboard())
    else:
        await message.answer("❌ Ошибка.")


@router.message(EditWallet.new_note, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def process_note_edit(
    message: Message, state: FSMContext, repo: Repository, session: SessionManager, audit: AuditLogger,
) -> None:
    note = message.text or ""
    telegram_id = message.from_user.id
    password = session.get_password(telegram_id)
    user = await repo.get_user(telegram_id)
    if password is None or user is None:
        await state.clear()
        return

    data = await state.get_data()
    enc_note = None
    if note.strip() != "-":
        enc_note = encrypt_seed(note.strip(), password, user.salt)

    ok = await repo.update_wallet_note(
        data["edit_wallet_id"], telegram_id, enc_note, decoy=data["decoy"],
    )
    await state.clear()
    if ok:
        await audit.log(telegram_id, "update_note")
        await message.answer("✅ Заметка обновлена.", reply_markup=main_menu_keyboard())
