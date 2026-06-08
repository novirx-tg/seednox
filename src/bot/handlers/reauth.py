"""Повторная проверка пароля перед критическими действиями."""

import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from src.bot.helpers import verify_master_password
from src.bot.keyboards import MENU_BUTTONS, cancel_keyboard, main_menu_keyboard
from src.bot.states import ReAuth
from src.crypto import decrypt_seed, encrypt_seed
from src.database.repository import Repository
from src.security.audit import AuditLogger
from src.security.backup import create_encrypted_backup, wallet_to_backup_item
from src.security.session import SessionManager

router = Router()


async def _start_reauth(
    callback: CallbackQuery,
    state: FSMContext,
    action: str,
    wallet_id: int | None = None,
) -> None:
    data = {"reauth_action": action}
    if wallet_id is not None:
        data["wallet_id"] = wallet_id
    await state.update_data(**data)
    await state.set_state(ReAuth.password)
    await callback.message.answer(
        "🔐 Подтвердите мастер-паролем:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view:"))
async def reauth_view(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Сейф заблокирован", show_alert=True)
        return
    wallet_id = int(callback.data.split(":")[1])
    await _start_reauth(callback, state, "view", wallet_id)


@router.callback_query(F.data.startswith("export:"))
async def reauth_export(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Сейф заблокирован", show_alert=True)
        return
    wallet_id = int(callback.data.split(":")[1])
    await _start_reauth(callback, state, "export", wallet_id)


@router.callback_query(F.data.startswith("delete:"))
async def reauth_delete(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Сейф заблокирован", show_alert=True)
        return
    wallet_id = int(callback.data.split(":")[1])
    await _start_reauth(callback, state, "delete", wallet_id)


@router.callback_query(F.data == "delete_account")
async def reauth_delete_account(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Сейф заблокирован", show_alert=True)
        return
    await _start_reauth(callback, state, "delete_account")


@router.callback_query(F.data == "backup")
async def reauth_backup(callback: CallbackQuery, state: FSMContext, session: SessionManager) -> None:
    if not session.peek_unlocked(callback.from_user.id):
        await callback.answer("Сейф заблокирован", show_alert=True)
        return
    if session.is_duress_mode(callback.from_user.id):
        await callback.answer("Недоступно в duress-режиме", show_alert=True)
        return
    await _start_reauth(callback, state, "backup")
    await callback.answer()


@router.message(ReAuth.password, F.text == "❌ Отмена")
async def cancel_reauth(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_keyboard())


@router.message(ReAuth.password, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def process_reauth(
    message: Message,
    state: FSMContext,
    repo: Repository,
    session: SessionManager,
    audit: AuditLogger,
) -> None:
    password = message.text or ""
    await message.delete()
    telegram_id = message.from_user.id
    user = await repo.get_user(telegram_id)
    if user is None:
        await state.clear()
        return

    if not await verify_master_password(user, password):
        await audit.log(telegram_id, "reauth_fail")
        await message.answer("❌ Неверный пароль.")
        await state.clear()
        return

    data = await state.get_data()
    action = data.get("reauth_action")
    wallet_id = data.get("wallet_id")
    decoy = session.is_duress_mode(telegram_id)
    await state.clear()

    if action == "view" and wallet_id:
        await _do_view(message, repo, audit, telegram_id, wallet_id, password, user.salt, decoy)
    elif action == "export" and wallet_id:
        await _do_export(message, repo, audit, telegram_id, wallet_id, password, user.salt, decoy)
    elif action == "delete" and wallet_id:
        await _do_delete(message, repo, audit, telegram_id, wallet_id, decoy)
    elif action == "delete_account":
        await _do_delete_account(message, repo, session, audit, telegram_id)
    elif action == "backup":
        await _do_backup(message, repo, audit, telegram_id, password, user.salt)


async def _do_view(
    message, repo, audit, telegram_id, wallet_id, password, salt, decoy,
) -> None:
    wallet = await repo.get_wallet(wallet_id, telegram_id, decoy=decoy)
    if wallet is None:
        await message.answer("Кошелёк не найден.")
        return
    try:
        seed = decrypt_seed(wallet.encrypted_seed, password, salt)
    except Exception:
        await message.answer("❌ Ошибка расшифровки.")
        return
    await audit.log(telegram_id, "view_seed", wallet.name)
    sent = await message.answer(
        f"👛 <b>{wallet.name}</b>\n\n<code>{seed}</code>\n\n"
        "⚠️ Удалится через 60 сек.",
        parse_mode="HTML",
    )

    async def _del():
        await asyncio.sleep(60)
        try:
            await sent.delete()
        except Exception:
            pass

    asyncio.create_task(_del())


async def _do_export(
    message, repo, audit, telegram_id, wallet_id, password, salt, decoy,
) -> None:
    wallet = await repo.get_wallet(wallet_id, telegram_id, decoy=decoy)
    if wallet is None:
        return
    item = wallet_to_backup_item(wallet.name, wallet.encrypted_seed, wallet.encrypted_note)
    blob = create_encrypted_backup([item], password, salt)
    await audit.log(telegram_id, "export_wallet", wallet.name)
    doc = BufferedInputFile(blob, filename=f"seednox_{wallet.name}.snx")
    await message.answer_document(
        doc,
        caption=f"📤 Экспорт «{wallet.name}». Храните в безопасности.",
    )


async def _do_delete(message, repo, audit, telegram_id, wallet_id, decoy) -> None:
    wallet = await repo.get_wallet(wallet_id, telegram_id, decoy=decoy)
    if wallet and await repo.delete_wallet(wallet_id, telegram_id, decoy=decoy):
        await audit.log(telegram_id, "delete_wallet", wallet.name)
        await message.answer(f"✅ «{wallet.name}» удалён.")
    else:
        await message.answer("❌ Не найден.")


async def _do_delete_account(message, repo, session, audit, telegram_id) -> None:
    await repo.delete_user(telegram_id)
    session.lock(telegram_id)
    await audit.log(telegram_id, "delete_account")
    await message.answer("✅ Аккаунт удалён. /register для новой регистрации.")


async def _do_backup(message, repo, audit, telegram_id, password, salt) -> None:
    wallets = await repo.get_wallets(telegram_id, decoy=False)
    if not wallets:
        await message.answer("Нет кошельков для бэкапа.")
        return
    items = [
        wallet_to_backup_item(w.name, w.encrypted_seed, w.encrypted_note) for w in wallets
    ]
    blob = create_encrypted_backup(items, password, salt)
    await audit.log(telegram_id, "backup", f"{len(wallets)} кошельков")
    doc = BufferedInputFile(blob, filename="seednox_backup.snx")
    await message.answer_document(doc, caption=f"💾 Бэкап: {len(wallets)} кошельков.")
