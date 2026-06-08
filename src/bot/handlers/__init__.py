from aiogram import Router

from .fallback import catchall_router
from .navigation import router as navigation_router
from .registration import router as registration_router
from .reauth import router as reauth_router
from .security_settings import router as security_settings_router
from .settings import router as settings_router
from .unlock import router as unlock_router
from .wallets import router as wallets_router


def setup_routers() -> Router:
    router = Router()
    # Навигация ПЕРВОЙ — команды и меню из любого состояния
    router.include_router(navigation_router)
    router.include_router(registration_router)
    router.include_router(unlock_router)
    router.include_router(wallets_router)
    router.include_router(reauth_router)
    router.include_router(settings_router)
    router.include_router(security_settings_router)
    router.include_router(catchall_router)
    return router
