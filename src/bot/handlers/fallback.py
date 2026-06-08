from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.states import (
    AddWallet,
    BackupRestore,
    EditWallet,
    Registration,
    ReAuth,
    SearchWallet,
    SetupDuress,
    SetupPin,
    Unlock,
)

catchall_router = Router()

_INPUT_STATES = (
    Registration,
    Unlock,
    AddWallet,
    EditWallet,
    SearchWallet,
    ReAuth,
    BackupRestore,
    SetupPin,
    SetupDuress,
)

_HINTS = {
    "Registration:risk_ack": "нажмите «Я понимаю риски»",
    "Registration:password": "введите мастер-пароль",
    "Registration:password_confirm": "повторите пароль",
    "Unlock:password": "введите пароль (или /unlock заново)",
    "Unlock:pin": "введите PIN",
    "AddWallet:name": "название кошелька",
    "AddWallet:note": "заметка или «-»",
    "AddWallet:seed": "сид-фраза",
    "ReAuth:password": "подтвердите паролем",
    "BackupRestore:waiting_file": "отправьте файл .snx",
    "BackupRestore:password": "пароль от бэкапа",
}


@catchall_router.message(StateFilter(*_INPUT_STATES))
async def hint_in_state(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Отправьте текстовое сообщение.")
        return
    current = await state.get_state()
    hint = _HINTS.get(current or "", "завершите шаг")
    await message.answer(
        f"Сейчас: {hint}.\n\n"
        "Любая команда (/start, /unlock) или кнопка меню сбросит шаг.",
    )
