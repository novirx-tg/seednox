from aiogram.types import Message

from src.bot.keyboards import locked_keyboard
from src.crypto import verify_password
from src.database.models import User
from src.database.repository import Repository
from src.security.audit import AuditLogger
from src.security.session import SessionManager


async def reply_locked(message: Message) -> None:
    await message.answer(
        "🔒 Сейф заблокирован.\n\nНажмите 🔓 Разблокировать или /unlock",
        reply_markup=locked_keyboard(),
    )


def is_active(session: SessionManager, telegram_id: int) -> bool:
    if not session.peek_unlocked(telegram_id):
        return False
    session.touch(telegram_id)
    return True


def use_decoy(session: SessionManager, telegram_id: int) -> bool:
    return session.is_duress_mode(telegram_id)


async def verify_user_password(user: User, password: str) -> bool:
    if verify_password(user.password_hash, password):
        return True
    if user.duress_password_hash and verify_password(user.duress_password_hash, password):
        return True
    return False


async def verify_master_password(user: User, password: str) -> bool:
    return verify_password(user.password_hash, password)


def is_duress_password(user: User, password: str) -> bool:
    if not user.duress_password_hash:
        return False
    return verify_password(user.duress_password_hash, password)


async def log_action(
    audit: AuditLogger,
    telegram_id: int,
    action: str,
    details: str | None = None,
) -> None:
    await audit.log(telegram_id, action, details)
