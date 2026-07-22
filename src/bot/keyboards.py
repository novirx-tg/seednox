from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from src.database.models import Wallet

SLOGAN = "🛡 Ваши сид-фразы всегда под нашей защитой!"

MENU_BUTTONS = frozenset({
    "📋 Мои кошельки",
    "➕ Добавить кошелёк",
    "🔍 Поиск",
    "🔒 Заблокировать",
    "⚙️ Настройки",
    "❌ Отмена",
    "🔓 Разблокировать",
})


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Мои кошельки")
    builder.button(text="➕ Добавить кошелёк")
    builder.button(text="🔍 Поиск")
    builder.button(text="🔒 Заблокировать")
    builder.button(text="⚙️ Настройки")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def locked_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔓 Разблокировать")
    return builder.as_markup(resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def risk_ack_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Я понимаю риски", callback_data="risk_accept"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="risk_cancel"))
    return builder.as_markup()


def wallets_list_keyboard(wallets: list[Wallet]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for wallet in wallets:
        builder.button(text=f"👛 {wallet.name}", callback_data=f"wallet:{wallet.id}")
    builder.adjust(1)
    return builder.as_markup()


def wallet_actions_keyboard(wallet_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👁 Сид-фраза", callback_data=f"view:{wallet_id}"),
        InlineKeyboardButton(text="📤 Экспорт", callback_data=f"export:{wallet_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"rename:{wallet_id}"),
        InlineKeyboardButton(text="📝 Заметка", callback_data=f"note:{wallet_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{wallet_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_list"),
    )
    return builder.as_markup()


def confirm_keyboard(action: str, wallet_id: int | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    data_yes = f"confirm_{action}:{wallet_id}" if wallet_id is not None else f"confirm_{action}"
    data_no = f"cancel_{action}:{wallet_id}" if wallet_id is not None else f"cancel_{action}"
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=data_yes),
        InlineKeyboardButton(text="❌ Нет", callback_data=data_no),
    )
    return builder.as_markup()


def settings_keyboard(pin_enabled: bool = False, duress_enabled: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    pin_label = "🔢 PIN: включён" if pin_enabled else "🔢 Настроить PIN"
    duress_label = "🎭 Duress: включён" if duress_enabled else "🎭 Настроить duress-пароль"
    builder.row(InlineKeyboardButton(text=pin_label, callback_data="setup_pin"))
    builder.row(InlineKeyboardButton(text=duress_label, callback_data="setup_duress"))
    builder.row(InlineKeyboardButton(text="🎭 Ложные кошельки", callback_data="decoy_wallets"))
    builder.row(InlineKeyboardButton(text="💾 Бэкап", callback_data="backup"))
    builder.row(InlineKeyboardButton(text="📥 Восстановление", callback_data="restore"))
    builder.row(InlineKeyboardButton(text="📜 Журнал активности", callback_data="audit_log"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить аккаунт", callback_data="delete_account"))
    builder.row(InlineKeyboardButton(text="📖 О проекте", callback_data="about"))
    return builder.as_markup()
