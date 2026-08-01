import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from src import __version__
from src.bot.handlers import setup_routers
from src.bot.middlewares import (
    AccessControlMiddleware,
    CallbackAnswerMiddleware,
    SecurityMiddleware,
    UserLockMiddleware,
)
from src.config import get_settings
from src.database.repository import Repository
from src.security.audit import AuditLogger
from src.security.session import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    if not settings.bot_token.get_secret_value():
        logger.error("BOT_TOKEN не задан. Скопируйте .env.example → .env")
        sys.exit(1)

    if not settings.allowed_user_ids:
        logger.warning(
            "⚠️ ВНИМАНИЕ: ALLOWED_USER_IDS не задан в .env! "
            "Бот доступен ЛЮБОМУ пользователю Telegram. "
            "Настоятельно рекомендуется ограничить доступ: ALLOWED_USER_IDS=your_telegram_id"
        )
    else:
        logger.info("Контроль доступа активен для %d Telegram ID", len(settings.allowed_user_ids))

    db_key = (
        settings.db_encryption_key.get_secret_value()
        if settings.db_encryption_key
        else None
    )
    repo = Repository(settings.database_path, encryption_key=db_key)
    await repo.connect()

    stats = await repo.get_stats()
    logger.info("БД: %s | users=%d wallets=%d", repo.db_path, stats["users"], stats["wallets"])

    session = SessionManager(settings.session_timeout)
    audit = AuditLogger(repo)

    # Обход блокировок Telegram API (HTTP/SOCKS5 Прокси и API Зеркала)
    bot_session = None
    if settings.telegram_proxy or settings.telegram_api_url:
        from aiogram.client.session.aiohttp import AiohttpSession
        session_kwargs = {}
        if settings.telegram_proxy:
            session_kwargs["proxy"] = settings.telegram_proxy
            logger.info("Подключен Telegram Proxy: %s", settings.telegram_proxy)
        if settings.telegram_api_url:
            from aiogram.client.telegram import TelegramAPIServer
            session_kwargs["api"] = TelegramAPIServer.from_base(settings.telegram_api_url)
            logger.info("Используется кастомное зеркало Telegram API: %s", settings.telegram_api_url)
        bot_session = AiohttpSession(**session_kwargs)

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=bot_session,
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp["repo"] = repo
    dp["session"] = session
    dp["audit"] = audit

    @dp.errors()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception("Ошибка обработки update: %s", event.exception)
        update = event.update
        try:
            if update.message:
                await update.message.answer(
                    "⚠️ Произошла ошибка. Попробуйте /start",
                )
            elif update.callback_query:
                await update.callback_query.answer("Ошибка", show_alert=True)
        except Exception:
            pass

    dp.update.outer_middleware(AccessControlMiddleware(settings.allowed_user_ids))
    dp.update.middleware(UserLockMiddleware())
    dp.update.middleware(SecurityMiddleware())
    dp.update.middleware(CallbackAnswerMiddleware())
    dp.include_router(setup_routers())

    me = await bot.get_me()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Seednox v%s запущен (@%s) — один экземпляр!", __version__, me.username)

    try:
        # handle_as_tasks=False — строгая очередь, без гонок FSM
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await repo.close()
        await bot.session.close()
        logger.info("Seednox остановлен")


if __name__ == "__main__":
    asyncio.run(main())
