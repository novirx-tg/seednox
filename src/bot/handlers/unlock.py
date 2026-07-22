from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.helpers import is_duress_password, log_action
from src.bot.keyboards import MENU_BUTTONS, cancel_keyboard, locked_keyboard, main_menu_keyboard
from src.bot.states import Unlock
from src.config import get_settings
from src.crypto import verify_password
from src.database.repository import Repository
from src.security.audit import AuditLogger
from src.security.session import SessionManager

router = Router()


@router.message(Unlock.password, F.text == "❌ Отмена")
@router.message(Unlock.pin, F.text == "❌ Отмена")
async def cancel_unlock(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=locked_keyboard())


@router.message(
    Unlock.password, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS),
)
async def process_unlock_password(
    message: Message,
    state: FSMContext,
    repo: Repository,
    session: SessionManager,
    audit: AuditLogger,
) -> None:
    settings = get_settings()
    telegram_id = message.from_user.id
    password = message.text or ""
    await message.delete()

    locked, remaining = await repo.get_login_lock(telegram_id)
    if locked:
        await message.answer(
            f"🚫 Слишком много попыток. Через {remaining // 60} мин {remaining % 60} сек.",
            reply_markup=locked_keyboard(),
        )
        await state.clear()
        return

    user = await repo.get_user(telegram_id)
    if user is None:
        await state.clear()
        return

    is_duress = is_duress_password(user, password)
    is_master = verify_password(user.password_hash, password)

    if not is_master and not is_duress:
        now_locked, dur = await repo.record_login_failure(
            telegram_id, settings.max_password_attempts, settings.lockout_duration,
        )
        await audit.log(telegram_id, "unlock_fail")
        if now_locked:
            await message.answer(f"❌ Неверный пароль. Блокировка на {dur // 60} мин.")
        else:
            await message.answer("❌ Неверный пароль. /unlock")
        await state.clear()
        return

    await repo.reset_login_attempts(telegram_id)

    if is_duress:
        session.unlock(telegram_id, password, is_duress=True, pin_required=False)
        await state.clear()
        await audit.log(telegram_id, "unlock_duress")
        await message.answer("🔓 Сейф разблокирован.", reply_markup=main_menu_keyboard(), parse_mode="HTML")
        return

    pin_required = user.pin_enabled and user.pin_hash is not None
    session.unlock(telegram_id, password, is_duress=False, pin_required=pin_required)

    if pin_required:
        await state.set_state(Unlock.pin)
        await message.answer("🔢 Введите 6-значный PIN:", reply_markup=cancel_keyboard())
        return

    await state.clear()
    await audit.log(telegram_id, "unlock")
    remaining = session.format_remaining(telegram_id)
    await message.answer(
        f"🔓 <b>Сейф разблокирован!</b>\n⏱ Через: {remaining}",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Unlock.pin, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def process_unlock_pin(
    message: Message, state: FSMContext, repo: Repository, session: SessionManager, audit: AuditLogger,
) -> None:
    settings = get_settings()
    telegram_id = message.from_user.id
    pin = (message.text or "").strip()
    await message.delete()

    if not pin.isdigit() or len(pin) != 6:
        await message.answer("PIN должен быть 6 цифр.")
        return

    user = await repo.get_user(telegram_id)
    if user is None or not user.pin_hash:
        await state.clear()
        return

    if not verify_password(user.pin_hash, pin):
        now_locked, dur = await repo.record_login_failure(
            telegram_id, settings.max_password_attempts, settings.lockout_duration,
        )
        await audit.log(telegram_id, "pin_fail")
        if now_locked:
            session.lock(telegram_id)
            await message.answer(f"🚫 Блокировка на {dur // 60} мин.", reply_markup=locked_keyboard())
        else:
            await message.answer("❌ Неверный PIN.")
        await state.clear()
        return

    session.verify_pin(telegram_id)
    await repo.reset_login_attempts(telegram_id)
    await state.clear()
    await audit.log(telegram_id, "unlock")
    await message.answer("🔓 PIN принят. Сейф открыт.", reply_markup=main_menu_keyboard(), parse_mode="HTML")
