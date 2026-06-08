from src.database.repository import Repository


class AuditLogger:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    async def log(self, telegram_id: int, action: str, details: str | None = None) -> None:
        await self._repo.log_audit(telegram_id, action, details)

    async def get_recent(self, telegram_id: int, limit: int = 15) -> list:
        return await self._repo.get_audit_log(telegram_id, limit)
