import gc
import time
from dataclasses import dataclass, field


@dataclass
class UserSession:
    telegram_id: int
    _password_bytes: bytearray | None = field(default=None, repr=False)
    is_duress: bool = False
    pin_verified: bool = True
    unlocked_at: float = field(default_factory=time.time)

    def __init__(
        self,
        telegram_id: int,
        password: str | bytes | bytearray,
        is_duress: bool = False,
        pin_verified: bool = True,
    ) -> None:
        self.telegram_id = telegram_id
        if isinstance(password, str):
            self._password_bytes = bytearray(password.encode("utf-8"))
        else:
            self._password_bytes = bytearray(password)
        self.is_duress = is_duress
        self.pin_verified = pin_verified
        self.unlocked_at = time.time()

    @property
    def password(self) -> str | None:
        """Декодирует пароль из bytearray. Для обратной совместимости."""
        if self._password_bytes is None:
            return None
        return self._password_bytes.decode("utf-8")

    def get_password_bytes(self) -> bytearray | None:
        return self._password_bytes

    def zeroize(self) -> None:
        """Перезаписывает память пароля нулями (0x00) и очищает буфер."""
        if self._password_bytes is not None:
            for i in range(len(self._password_bytes)):
                self._password_bytes[i] = 0
            self._password_bytes.clear()
            self._password_bytes = None

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
    """In-memory хранилище активных сессий с безопасной очисткой RAM (Zeroize)."""

    def __init__(self, timeout: int) -> None:
        self._timeout = timeout
        self._sessions: dict[int, UserSession] = {}

    def unlock(
        self,
        telegram_id: int,
        password: str | bytes | bytearray,
        *,
        is_duress: bool = False,
        pin_required: bool = False,
    ) -> None:
        # Если уже была активная сессия для этого пользователя — затираем её
        old_session = self._sessions.pop(telegram_id, None)
        if old_session:
            old_session.zeroize()

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
        session = self._sessions.pop(telegram_id, None)
        if session:
            session.zeroize()
        gc.collect()

    def lock_all(self) -> None:
        for session in self._sessions.values():
            session.zeroize()
        self._sessions.clear()
        gc.collect()

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

    def get_password_bytes(self, telegram_id: int) -> bytearray | None:
        session = self._get(telegram_id)
        if session is None or not session.is_fully_unlocked():
            return None
        session.refresh()
        return session.get_password_bytes()

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
