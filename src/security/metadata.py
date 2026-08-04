"""
Шифрование метаданных (названий записей и деталей аудит-лога).

Раньше эти поля лежали в БД открытым текстом — при краже файла базы было видно
ярлыки вроде «Ledger 20 ETH» и историю действий. :class:`MetaCipher` шифрует их
той же схемой, что и сами секреты (AES-256-GCM), но **ключ выводится один раз**
(Argon2id дорогой — вызывать его на каждое имя в списке нельзя), после чего
переиспользуется для всех метаданных пользователя.

Формат хранимого значения: ``META_PREFIX + base64(nonce || ciphertext)``.
Старые (незашифрованные) значения не имеют префикса и возвращаются как есть —
это обеспечивает обратную совместимость и позволяет лениво мигрировать базу.
"""

from __future__ import annotations

import base64
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.crypto.kdf import derive_key
from src.security.memory import wipe

# Текстовый маркер зашифрованного метаполя (v1). Хранится в TEXT-колонках.
META_PREFIX = "snxm1:"


def is_encrypted(stored: object) -> bool:
    """True, если значение уже зашифровано этой схемой."""
    return isinstance(stored, str) and stored.startswith(META_PREFIX)


class MetaCipher:
    """Шифратор метаданных с однократной деривацией ключа.

    Ключ совпадает с ключом шифрования секретов (тот же ``derive_key``), поэтому
    отдельного пароля не требуется. Держите объект только на время
    разблокированной сессии и вызывайте :meth:`wipe` при блокировке.
    """

    __slots__ = ("_key",)

    def __init__(self, password: str | bytes | bytearray, salt: bytes) -> None:
        # derive_key возвращает bytes; держим в bytearray, чтобы затирать при блокировке.
        self._key: bytearray | None = bytearray(derive_key(password, salt))

    def _aesgcm(self) -> AESGCM:
        if self._key is None:
            raise ValueError("MetaCipher стёрт — сессия заблокирована")
        return AESGCM(bytes(self._key))

    def encrypt(self, text: str | None) -> str | None:
        """Шифрует строку метаданных. ``None`` → ``None`` (пустое поле)."""
        if text is None:
            return None
        nonce = secrets.token_bytes(12)
        ciphertext = self._aesgcm().encrypt(nonce, text.encode("utf-8"), None)
        return META_PREFIX + base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, stored: str | None) -> str | None:
        """Расшифровывает значение. Старый открытый текст возвращается как есть."""
        if stored is None:
            return None
        if not is_encrypted(stored):
            return stored  # legacy plaintext — ещё не мигрировано
        raw = base64.b64decode(stored[len(META_PREFIX):])
        nonce, ciphertext = raw[:12], raw[12:]
        return self._aesgcm().decrypt(nonce, ciphertext, None).decode("utf-8")

    @staticmethod
    def is_encrypted(stored: object) -> bool:
        return is_encrypted(stored)

    def wipe(self) -> None:
        wipe(self._key)
        self._key = None

    def __enter__(self) -> "MetaCipher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.wipe()

    def __del__(self) -> None:
        try:
            self.wipe()
        except Exception:
            pass
