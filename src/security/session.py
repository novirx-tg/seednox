import time
from dataclasses import dataclass, field


@dataclass
class UserSession:
    telegram_id: int
    password: str
    is_duress: bool = False
    pin_verified: bool = True
    unlocked_at: float = field(default_factory=time.time)

    def is_expired(self, timeout: int) -> bool:
        return time.time() - self.unlocked_at > timeout

    def refresh(self) -> None:
        self.unlocked_at = time.time()

    def remaining(self, timeout: int) -> int:
        left = timeout - (time.time() - self.unlocked_at)
        return max(0, int(left))

    def is_fully_unlocked(self) -> bool:
        return self.pin_verified


class SessionManager:
    """In-memory хранилище активных сессий. Пароль никогда не пишется на диск."""

    def __init__(self, timeout: int) -> None:
        self._timeout = timeout
        self._sessions: dict[int, UserSession] = {}

    def unlock(
        self,
        telegram_id: int,
        password: str,
        *,
        is_duress: bool = False,
        pin_required: bool = False,
    ) -> None:
        self._sessions[telegram_id] = UserSession(
            telegram_id=telegram_id,
            password=password,
            is_duress=is_duress,
            pin_verified=not pin_required,
        )

    def verify_pin(self, telegram_id: int) -> None:
        session = self._sessions.get(telegram_id)
        if session:
            session.pin_verified = True
            session.refresh()

    def is_duress_mode(self, telegram_id: int) -> bool:
        session = self._sessions.get(telegram_id)
        return session.is_duress if session else False

    def lock(self, telegram_id: int) -> None:
        self._sessions.pop(telegram_id, None)

    def _get(self, telegram_id: int) -> UserSession | None:
        session = self._sessions.get(telegram_id)
        if session is None:
            return None
        if session.is_expired(self._timeout):
            self.lock(telegram_id)
            return None
        return session

    def peek_unlocked(self, telegram_id: int) -> bool:
        session = self._get(telegram_id)
        return session is not None and session.is_fully_unlocked()

    def peek_pending_pin(self, telegram_id: int) -> bool:
        session = self._get(telegram_id)
        return session is not None and not session.pin_verified

    def touch(self, telegram_id: int) -> bool:
        session = self._get(telegram_id)
        if session is None or not session.is_fully_unlocked():
            return False
        session.refresh()
        return True

    def remaining_seconds(self, telegram_id: int) -> int:
        session = self._get(telegram_id)
        if session is None:
            return 0
        return session.remaining(self._timeout)

    def get_password(self, telegram_id: int) -> str | None:
        session = self._get(telegram_id)
        if session is None or not session.is_fully_unlocked():
            return None
        session.refresh()
        return session.password

    def is_unlocked(self, telegram_id: int) -> bool:
        return self.peek_unlocked(telegram_id)

    def format_remaining(self, telegram_id: int) -> str:
        seconds = self.remaining_seconds(telegram_id)
        if seconds <= 0:
            return "истекла"
        minutes = seconds // 60
        secs = seconds % 60
        if minutes > 0:
            return f"{minutes} мин {secs} сек"
        return f"{secs} сек"
