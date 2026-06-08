import logging
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


def _sqlcipher_connector(db_path: Path, key: str):
    def connector() -> Any:
        import sqlcipher3.dbapi2 as sqlcipher  # type: ignore[import-untyped]

        conn = sqlcipher.connect(str(db_path))
        conn.execute("PRAGMA key = ?", (key,))
        conn.execute("PRAGMA cipher_compatibility = 4")
        return conn

    return connector


async def open_database(db_path: Path, encryption_key: str | None) -> aiosqlite.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if encryption_key:
        try:
            connector = _sqlcipher_connector(db_path, encryption_key)
            conn = await aiosqlite.connect(db_path, connector=connector)
            logger.info("SQLCipher: база зашифрована")
            return conn
        except ImportError:
            logger.warning(
                "sqlcipher3 не установлен — БД без шифрования файла. "
                "Для SQLCipher: pip install sqlcipher3 (Linux/Docker)"
            )
        except Exception as exc:
            logger.error("SQLCipher ошибка: %s — fallback на SQLite", exc)

    conn = await aiosqlite.connect(db_path)
    return conn
