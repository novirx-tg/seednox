"""
Best-effort затирание секретов в памяти.

Важное ограничение Python: обычные ``str`` и ``bytes`` неизменяемы, их нельзя
надёжно занулить (интернирование строк, копии в буферах интерпретатора, своп).
Поэтому единственный практичный способ реально стереть секрет — держать его
в ``bytearray`` и перезаписать нулями через :func:`wipe`.

Модуль даёт:
* :func:`wipe` — обнуляет один или несколько ``bytearray`` на месте.
* :class:`SecretBytes` — обёртка над ``bytearray`` с ленивым доступом и
  гарантированным затиранием (в т.ч. через контекстный менеджер и ``__del__``).
"""

from __future__ import annotations

import gc


def wipe(*buffers: bytearray | None) -> None:
    """Обнуляет переданные ``bytearray`` на месте. ``None`` игнорируются.

    ``bytes``/``str`` занулить нельзя — такие значения молча пропускаются,
    вызывающий код должен изначально хранить секрет в ``bytearray``.
    """
    for buf in buffers:
        if isinstance(buf, bytearray):
            for i in range(len(buf)):
                buf[i] = 0


def to_secret_bytearray(secret: str | bytes | bytearray) -> bytearray:
    """Нормализует секрет в свежий ``bytearray`` (который потом можно занулить)."""
    if isinstance(secret, bytearray):
        return secret
    if isinstance(secret, bytes):
        return bytearray(secret)
    return bytearray(secret.encode("utf-8"))


class SecretBytes:
    """Контейнер для секрета, который можно надёжно стереть.

    Хранит данные в ``bytearray``. После :meth:`wipe` (или выхода из ``with``)
    буфер зануляется. Не логируется и не показывается в repr.
    """

    __slots__ = ("_buf",)

    def __init__(self, secret: str | bytes | bytearray) -> None:
        self._buf: bytearray | None = to_secret_bytearray(secret)

    def bytes(self) -> bytes:
        """Возвращает копию секрета как ``bytes`` для разовой крипто-операции."""
        if self._buf is None:
            raise ValueError("Секрет уже стёрт из памяти")
        return bytes(self._buf)

    def wipe(self) -> None:
        wipe(self._buf)
        self._buf = None

    @property
    def wiped(self) -> bool:
        return self._buf is None

    def __enter__(self) -> "SecretBytes":
        return self

    def __exit__(self, *exc: object) -> None:
        self.wipe()

    def __del__(self) -> None:
        try:
            self.wipe()
        except Exception:
            pass

    def __repr__(self) -> str:  # никогда не раскрываем содержимое
        return "<SecretBytes wiped>" if self._buf is None else "<SecretBytes •••>"


def collect() -> None:
    """Форсирует сборку мусора — помогает быстрее убрать осиротевшие копии секретов."""
    gc.collect()
