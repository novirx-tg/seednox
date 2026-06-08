from aiogram import F, Router
from aiogram.types import CallbackQuery

from src import GITHUB_REPO, __version__
from src.bot.keyboards import SLOGAN

router = Router()


@router.callback_query(F.data == "about")
async def about_project(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        f"🛡 <b>Seednox</b> v{__version__}\n<i>{SLOGAN}</i>\n\n"
        f"🔗 {GITHUB_REPO}",
        parse_mode="HTML",
    )
    await callback.answer()
