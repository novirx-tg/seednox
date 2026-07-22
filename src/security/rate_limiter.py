import time
from dataclasses import dataclass, field


@dataclass
class AttemptRecord:
    attempts: int = 0
    locked_until: float = 0.0


class RateLimiter:
    """Ограничение попыток ввода пароля для защиты от брутфорса."""

    def __init__(self, max_attempts: int, lockout_duration: int) -> None:
        self._max_attempts = max_attempts
        self._lockout_duration = lockout_duration
        self._records: dict[int, AttemptRecord] = {}

    def is_locked(self, telegram_id: int) -> tuple[bool, int]:
        record = self._records.get(telegram_id)
        if record is None:
            return False, 0
        if record.locked_until > time.time():
            remaining = int(record.locked_until - time.time())
            return True, remaining
        if record.locked_until > 0:
            record.attempts = 0
            record.locked_until = 0.0
        return False, 0

    def record_failure(self, telegram_id: int) -> tuple[bool, int]:
        record = self._records.setdefault(telegram_id, AttemptRecord())
        record.attempts += 1
        if record.attempts >= self._max_attempts:
            record.locked_until = time.time() + self._lockout_duration
            record.attempts = 0
            return True, self._lockout_duration
        return False, 0

    def reset(self, telegram_id: int) -> None:
        self._records.pop(telegram_id, None)
