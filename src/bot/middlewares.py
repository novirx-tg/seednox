import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

logger = logging.getLogger(__name__)

SENSITIVE_STATES = {
    "Registration:password",
    "Registration:password_confirm",
    "Unlock:password",
    "Unlock:pin",
    "AddWallet:seed",
    "ReAuth:password",
    "BackupRestore:password",
    "SetupPin:pin",
    "SetupPin:pin_confirm",
    "SetupDuress:password",
    "SetupDuress:password_confirm",
}


class UserLockMiddleware(BaseMiddleware):
    """Обрабатывает сообщения одного пользователя строго по очереди."""

    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, Update):
            if event.message and event.message.from_user:
                user_id = event.message.from_user.id
            elif event.callback_query and event.callback_query.from_user:
                user_id = event.callback_query.from_user.id

        if user_id is None:
            return await handler(event, data)

        async with self._locks[user_id]:
            return await handler(event, data)


class SecurityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state = data.get("state")
        if state and isinstance(event, Message) and event.text:
            current = await state.get_state()
            if current in SENSITIVE_STATES:
                data["sensitive_message"] = True
        return await handler(event, data)


class CallbackAnswerMiddleware(BaseMiddleware):
    """Гарантирует ответ на callback, даже если хендлер упал."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)
        try:
            return await handler(event, data)
        except Exception:
            try:
                await event.answer("Ошибка обработки", show_alert=True)
            except Exception:
                pass
            raise
