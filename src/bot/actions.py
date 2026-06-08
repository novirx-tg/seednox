"""Общая логика навигации — вызывается из любого состояния FSM."""

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src import __version__
from src.bot.helpers import is_active, log_action, reply_locked, use_decoy
from src.bot.keyboards import SLOGAN, locked_keyboard, main_menu_keyboard, settings_keyboard, wallets_list_keyboard
from src.bot.states import Unlock
from src.database.repository import Repository
from src.security.audit import AuditLogger
from src.security.session import SessionManager


async def do_start(message: Message, repo: Repository, session: SessionManager) -> None:
    if not await repo.user_exists(message.from_user.id):
        await message.answer(
            f"👋 Добро пожаловать в <b>Seednox</b> v{__version__}!\n\n<i>{SLOGAN}</i>\n\n"
            "Для начала: /register",
            parse_mode="HTML",
        )
        return
    if session.peek_unlocked(message.from_user.id):
        remaining = session.format_remaining(message.from_user.id)
        await message.answer(
            f"🛡 Сейф открыт. ⏱ {remaining}\n<i>{SLOGAN}</i>",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "🔒 Сейф заблокирован.\n/unlock или 🔓 Разблокировать",
            reply_markup=locked_keyboard(),
        )


async def do_help(message: Message) -> None:
    await message.answer(
        f"🛡 <b>Seednox</b> v{__version__}\n\n"
        "<b>Команды:</b> /start /register /unlock /lock /status /help\n"
        "Меню работает из любого состояния.",
        parse_mode="HTML",
    )


async def do_register_prompt(message: Message, repo: Repository) -> None:
    if await repo.user_exists(message.from_user.id):
        await message.answer("⚠️ Уже зарегистрированы. /unlock")
        return
    await message.answer("Регистрация: /register")


async def do_unlock(message: Message, state: FSMContext, repo: Repository, session: SessionManager) -> None:
    if not await repo.user_exists(message.from_user.id):
        await message.answer("Сначала /register")
        return
    if session.peek_unlocked(message.from_user.id):
        remaining = session.format_remaining(message.from_user.id)
        await message.answer(f"🔓 Уже открыт. ⏱ {remaining}", reply_markup=main_menu_keyboard())
        return
    await state.set_state(Unlock.password)
    from src.bot.keyboards import cancel_keyboard
    await message.answer("🔐 Введите мастер-пароль:", reply_markup=cancel_keyboard())


async def do_lock(message: Message, session: SessionManager, audit: AuditLogger) -> None:
    tid = message.from_user.id
    if not session.peek_unlocked(tid) and not session.peek_pending_pin(tid):
        await message.answer("🔒 Уже заблокирован.", reply_markup=locked_keyboard())
        return
    session.lock(tid)
    await log_action(audit, tid, "lock")
    await message.answer("🔒 Заблокирован.", reply_markup=locked_keyboard())


async def do_status(message: Message, session: SessionManager) -> None:
    if session.peek_unlocked(message.from_user.id):
        mode = "duress" if session.is_duress_mode(message.from_user.id) else "обычный"
        remaining = session.format_remaining(message.from_user.id)
        await message.answer(
            f"🔓 Открыт ({mode}). ⏱ {remaining}",
            reply_markup=main_menu_keyboard(),
        )
    elif session.peek_pending_pin(message.from_user.id):
        from src.bot.keyboards import cancel_keyboard
        await message.answer("Введите PIN:", reply_markup=cancel_keyboard())
    else:
        await message.answer("🔒 Заблокирован.", reply_markup=locked_keyboard())


async def do_list_wallets(message: Message, repo: Repository, session: SessionManager) -> None:
    if not is_active(session, message.from_user.id):
        await reply_locked(message)
        return
    decoy = use_decoy(session, message.from_user.id)
    wallets = await repo.get_wallets(message.from_user.id, decoy=decoy)
    if not wallets:
        await message.answer("📭 Нет кошельков. ➕ Добавить")
        return
    await message.answer(
        f"📋 Кошельки ({len(wallets)}):",
        reply_markup=wallets_list_keyboard(wallets),
        parse_mode="HTML",
    )


async def do_settings(message: Message, repo: Repository, session: SessionManager) -> None:
    if not session.peek_unlocked(message.from_user.id):
        await reply_locked(message)
        return
    session.touch(message.from_user.id)
    user = await repo.get_user(message.from_user.id)
    await message.answer(
        "⚙️ <b>Настройки</b>",
        reply_markup=settings_keyboard(
            pin_enabled=user.pin_enabled if user else False,
            duress_enabled=bool(user and user.duress_password_hash),
        ),
        parse_mode="HTML",
    )
