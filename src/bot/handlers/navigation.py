"""
Приоритетный роутер: команды и меню работают ВСЕГДА,
даже посреди ввода пароля/сид-фразы. Сбрасывает FSM перед действием.
"""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot import actions
from src.bot.handlers.registration import start_registration
from src.database.repository import Repository
from src.security.audit import AuditLogger
from src.security.session import SessionManager

router = Router()


async def _reset(state: FSMContext) -> None:
    await state.clear()


@router.message(CommandStart())
async def nav_start(
    message: Message, state: FSMContext, repo: Repository, session: SessionManager,
) -> None:
    await _reset(state)
    await actions.do_start(message, repo, session)


@router.message(Command("help"))
async def nav_help(message: Message, state: FSMContext) -> None:
    await _reset(state)
    await actions.do_help(message)


@router.message(Command("register"))
async def nav_register(message: Message, state: FSMContext, repo: Repository) -> None:
    await _reset(state)
    await start_registration(message, state, repo)


@router.message(Command("unlock"))
@router.message(F.text == "🔓 Разблокировать")
async def nav_unlock(
    message: Message, state: FSMContext, repo: Repository, session: SessionManager,
) -> None:
    await _reset(state)
    await actions.do_unlock(message, state, repo, session)


@router.message(Command("lock"))
@router.message(F.text == "🔒 Заблокировать")
async def nav_lock(
    message: Message, state: FSMContext, session: SessionManager, audit: AuditLogger,
) -> None:
    await _reset(state)
    await actions.do_lock(message, session, audit)


@router.message(Command("status"))
async def nav_status(message: Message, state: FSMContext, session: SessionManager) -> None:
    await _reset(state)
    await actions.do_status(message, session)


@router.message(F.text == "📋 Мои кошельки")
async def nav_list(message: Message, state: FSMContext, repo: Repository, session: SessionManager) -> None:
    await _reset(state)
    await actions.do_list_wallets(message, repo, session)


@router.message(F.text == "⚙️ Настройки")
async def nav_settings(
    message: Message, state: FSMContext, repo: Repository, session: SessionManager,
) -> None:
    await _reset(state)
    await actions.do_settings(message, repo, session)


@router.message(F.text == "➕ Добавить кошелёк")
async def nav_add_wallet(
    message: Message, state: FSMContext, session: SessionManager, repo: Repository,
) -> None:
    await _reset(state)
    from src.bot.handlers.wallets import start_add_wallet
    await start_add_wallet(message, state, session, repo)


@router.message(F.text == "🔍 Поиск")
async def nav_search(message: Message, state: FSMContext, session: SessionManager) -> None:
    await _reset(state)
    from src.bot.handlers.wallets import start_search
    await start_search(message, state, session)
