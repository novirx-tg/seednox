from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import MENU_BUTTONS, cancel_keyboard, main_menu_keyboard, risk_ack_keyboard
from src.bot.states import Registration
from src.crypto import generate_salt, hash_password
from src.database.repository import Repository
from src.security.audit import AuditLogger
from src.security.password_strength import check_password_strength, format_strength
from src.security.session import SessionManager
from src.security.validators import validate_password

router = Router()

RISK_TEXT = (
    "⚠️ <b>Важно — прочитайте перед регистрацией</b>\n\n"
    "• Telegram <b>не шифрует</b> сообщения боту end-to-end\n"
    "• Сид-фразы проходят через серверы Telegram\n"
    "• Потеря мастер-пароля = <b>безвозвратная</b> потеря доступа\n"
    "• Для максимальной безопасности — <b>self-host</b> на своём сервере\n"
    "• Seednox — хранилище, не кошелёк\n\n"
    "Продолжая, вы подтверждаете, что понимаете эти риски."
)


async def start_registration(message: Message, state: FSMContext, repo: Repository) -> None:
    if await repo.user_exists(message.from_user.id):
        await message.answer("⚠️ Вы уже зарегистрированы. Используйте /unlock для входа.")
        return
    await state.set_state(Registration.risk_ack)
    await message.answer(RISK_TEXT, reply_markup=risk_ack_keyboard(), parse_mode="HTML")


@router.callback_query(Registration.risk_ack, F.data == "risk_accept")
async def risk_accepted(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Registration.password)
    await callback.message.edit_text(
        "🔐 <b>Создание мастер-пароля</b>\n\n"
        "Минимум 12 символов, заглавные + строчные + цифры.\n"
        "Рекомендуем оценку «хороший» или выше.\n\n"
        "⚠️ Пароль невозможно восстановить!",
        parse_mode="HTML",
    )
    await callback.message.answer("Введите пароль:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(Registration.risk_ack, F.data == "risk_cancel")
async def risk_cancelled(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Регистрация отменена.")
    await callback.answer()


@router.message(Registration.password, F.text == "❌ Отмена")
@router.message(Registration.password_confirm, F.text == "❌ Отмена")
async def cancel_registration(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Регистрация отменена.")


@router.message(
    Registration.password,
    F.text,
    ~F.text.startswith("/"),
    ~F.text.in_(MENU_BUTTONS),
)
async def process_password(message: Message, state: FSMContext) -> None:
    password = message.text or ""
    await message.delete()

    result = validate_password(password)
    if not result.valid:
        await message.answer(f"❌ {result.error}\n\nПопробуйте снова:")
        return

    strength = check_password_strength(password)
    if not strength.acceptable:
        await message.answer(
            f"{format_strength(password)}\n\n"
            "❌ Пароль слишком слабый. Используйте более сложный.",
        )
        return

    await state.update_data(password=password)
    await state.set_state(Registration.password_confirm)
    await message.answer(
        f"{format_strength(password)}\n\n🔁 Повторите пароль:",
        reply_markup=cancel_keyboard(),
    )


@router.message(
    Registration.password_confirm,
    F.text,
    ~F.text.startswith("/"),
    ~F.text.in_(MENU_BUTTONS),
)
async def process_password_confirm(
    message: Message,
    state: FSMContext,
    repo: Repository,
    session: SessionManager,
    audit: AuditLogger,
) -> None:
    password = message.text or ""
    await message.delete()

    data = await state.get_data()
    if password != data.get("password"):
        await message.answer("❌ Пароли не совпадают. Начните заново: /register")
        await state.clear()
        return

    telegram_id = message.from_user.id
    salt = generate_salt()
    password_hash = hash_password(password)
    now = datetime.now(timezone.utc)

    await repo.create_user(telegram_id, password_hash, salt, risk_accepted_at=now)
    session.unlock(telegram_id, password)
    await repo.reset_login_attempts(telegram_id)
    await audit.log(telegram_id, "register", "Регистрация завершена")
    await state.clear()

    await message.answer(
        "✅ <b>Регистрация завершена!</b>\n\n"
        "Сейф создан и разблокирован.\n"
        "В настройках: PIN, duress-пароль, бэкап.\n\n"
        "🔒 Не забудьте заблокировать сейф после работы.",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
