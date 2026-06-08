import time
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from src.database.connection import open_database
from src.database.models import AuditEntry, DecoyWallet, User, Wallet


class Repository:
    def __init__(self, db_path: Path, encryption_key: str | None = None) -> None:
        self._db_path = db_path
        self._encryption_key = encryption_key
        self._connection = None

    async def connect(self) -> None:
        self._connection = await open_database(self._db_path, self._encryption_key)
        self._connection.row_factory = aiosqlite.Row  # type: ignore[name-defined]
        await self._create_tables()
        await self._migrate()

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _create_tables(self) -> None:
        assert self._connection is not None
        await self._connection.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt BLOB NOT NULL,
                created_at TEXT NOT NULL,
                pin_hash TEXT,
                pin_enabled INTEGER NOT NULL DEFAULT 0,
                duress_password_hash TEXT,
                risk_accepted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                encrypted_seed BLOB NOT NULL,
                encrypted_note BLOB,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                UNIQUE(telegram_id, name)
            );

            CREATE TABLE IF NOT EXISTS decoy_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                encrypted_seed BLOB NOT NULL,
                encrypted_note BLOB,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                UNIQUE(telegram_id, name)
            );

            CREATE TABLE IF NOT EXISTS login_attempts (
                telegram_id INTEGER PRIMARY KEY,
                attempts INTEGER NOT NULL DEFAULT 0,
                locked_until REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_wallets_telegram_id ON wallets(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_decoy_telegram_id ON decoy_wallets(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_audit_telegram_id ON audit_log(telegram_id);
        """)
        await self._connection.commit()

    async def _migrate(self) -> None:
        assert self._connection is not None
        migrations = [
            "ALTER TABLE users ADD COLUMN pin_hash TEXT",
            "ALTER TABLE users ADD COLUMN pin_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN duress_password_hash TEXT",
            "ALTER TABLE users ADD COLUMN risk_accepted_at TEXT",
            "ALTER TABLE wallets ADD COLUMN encrypted_note BLOB",
        ]
        for sql in migrations:
            try:
                await self._connection.execute(sql)
                await self._connection.commit()
            except Exception:
                pass

    def _row_to_user(self, row) -> User:
        return User(
            telegram_id=row["telegram_id"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            created_at=datetime.fromisoformat(row["created_at"]),
            pin_hash=row["pin_hash"],
            pin_enabled=bool(row["pin_enabled"]),
            duress_password_hash=row["duress_password_hash"],
            risk_accepted_at=(
                datetime.fromisoformat(row["risk_accepted_at"])
                if row["risk_accepted_at"]
                else None
            ),
        )

    def _row_to_wallet(self, row) -> Wallet:
        return Wallet(
            id=row["id"],
            telegram_id=row["telegram_id"],
            name=row["name"],
            encrypted_seed=row["encrypted_seed"],
            encrypted_note=row["encrypted_note"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_decoy(self, row) -> DecoyWallet:
        return DecoyWallet(
            id=row["id"],
            telegram_id=row["telegram_id"],
            name=row["name"],
            encrypted_seed=row["encrypted_seed"],
            encrypted_note=row["encrypted_note"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def user_exists(self, telegram_id: int) -> bool:
        assert self._connection is not None
        cursor = await self._connection.execute(
            "SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,),
        )
        return await cursor.fetchone() is not None

    async def create_user(
        self,
        telegram_id: int,
        password_hash: str,
        salt: bytes,
        risk_accepted_at: datetime | None = None,
    ) -> User:
        assert self._connection is not None
        now = datetime.now(timezone.utc).isoformat()
        risk = risk_accepted_at.isoformat() if risk_accepted_at else now
        await self._connection.execute(
            """
            INSERT INTO users
            (telegram_id, password_hash, salt, created_at, risk_accepted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, password_hash, salt, now, risk),
        )
        await self._connection.commit()
        return await self.get_user(telegram_id)  # type: ignore[return-value]

    async def get_user(self, telegram_id: int) -> User | None:
        assert self._connection is not None
        cursor = await self._connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_user(row) if row else None

    async def update_pin(self, telegram_id: int, pin_hash: str | None, enabled: bool) -> None:
        assert self._connection is not None
        await self._connection.execute(
            "UPDATE users SET pin_hash = ?, pin_enabled = ? WHERE telegram_id = ?",
            (pin_hash, int(enabled), telegram_id),
        )
        await self._connection.commit()

    async def update_duress(self, telegram_id: int, duress_hash: str | None) -> None:
        assert self._connection is not None
        await self._connection.execute(
            "UPDATE users SET duress_password_hash = ? WHERE telegram_id = ?",
            (duress_hash, telegram_id),
        )
        await self._connection.commit()

    async def add_wallet(
        self,
        telegram_id: int,
        name: str,
        encrypted_seed: bytes,
        encrypted_note: bytes | None = None,
        *,
        decoy: bool = False,
    ) -> Wallet | DecoyWallet:
        assert self._connection is not None
        table = "decoy_wallets" if decoy else "wallets"
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self._connection.execute(
            f"""
            INSERT INTO {table}
            (telegram_id, name, encrypted_seed, encrypted_note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (telegram_id, name, encrypted_seed, encrypted_note, now, now),
        )
        await self._connection.commit()
        getter = self.get_decoy_wallet if decoy else self.get_wallet
        result = await getter(cursor.lastrowid, telegram_id)
        return result  # type: ignore[return-value]

    async def get_wallets(
        self, telegram_id: int, *, decoy: bool = False, search: str | None = None,
    ) -> list[Wallet] | list[DecoyWallet]:
        assert self._connection is not None
        table = "decoy_wallets" if decoy else "wallets"
        query = f"SELECT * FROM {table} WHERE telegram_id = ?"
        params: list = [telegram_id]
        if search:
            query += " AND name LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY name"
        cursor = await self._connection.execute(query, params)
        rows = await cursor.fetchall()
        mapper = self._row_to_decoy if decoy else self._row_to_wallet
        return [mapper(row) for row in rows]

    async def get_wallet(
        self, wallet_id: int, telegram_id: int, *, decoy: bool = False,
    ) -> Wallet | DecoyWallet | None:
        assert self._connection is not None
        table = "decoy_wallets" if decoy else "wallets"
        cursor = await self._connection.execute(
            f"SELECT * FROM {table} WHERE id = ? AND telegram_id = ?",
            (wallet_id, telegram_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_decoy(row) if decoy else self._row_to_wallet(row)

    async def get_decoy_wallet(self, wallet_id: int, telegram_id: int) -> DecoyWallet | None:
        result = await self.get_wallet(wallet_id, telegram_id, decoy=True)
        return result  # type: ignore[return-value]

    async def rename_wallet(
        self, wallet_id: int, telegram_id: int, new_name: str, *, decoy: bool = False,
    ) -> bool:
        assert self._connection is not None
        table = "decoy_wallets" if decoy else "wallets"
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self._connection.execute(
            f"UPDATE {table} SET name = ?, updated_at = ? WHERE id = ? AND telegram_id = ?",
            (new_name, now, wallet_id, telegram_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def update_wallet_note(
        self,
        wallet_id: int,
        telegram_id: int,
        encrypted_note: bytes | None,
        *,
        decoy: bool = False,
    ) -> bool:
        assert self._connection is not None
        table = "decoy_wallets" if decoy else "wallets"
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self._connection.execute(
            f"UPDATE {table} SET encrypted_note = ?, updated_at = ? WHERE id = ? AND telegram_id = ?",
            (encrypted_note, now, wallet_id, telegram_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def delete_wallet(
        self, wallet_id: int, telegram_id: int, *, decoy: bool = False,
    ) -> bool:
        assert self._connection is not None
        table = "decoy_wallets" if decoy else "wallets"
        cursor = await self._connection.execute(
            f"DELETE FROM {table} WHERE id = ? AND telegram_id = ?",
            (wallet_id, telegram_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def count_wallets(self, telegram_id: int, *, decoy: bool = False) -> int:
        assert self._connection is not None
        table = "decoy_wallets" if decoy else "wallets"
        cursor = await self._connection.execute(
            f"SELECT COUNT(*) as cnt FROM {table} WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0

    async def delete_user(self, telegram_id: int) -> bool:
        assert self._connection is not None
        await self._connection.execute(
            "DELETE FROM decoy_wallets WHERE telegram_id = ?", (telegram_id,),
        )
        cursor = await self._connection.execute(
            "DELETE FROM users WHERE telegram_id = ?", (telegram_id,),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def import_wallets(
        self,
        telegram_id: int,
        items: list[tuple[str, bytes, bytes | None]],
    ) -> int:
        count = 0
        for name, enc_seed, enc_note in items:
            try:
                await self.add_wallet(telegram_id, name, enc_seed, enc_note)
                count += 1
            except Exception:
                pass
        return count

    # --- Rate limit (persistent) ---

    async def get_login_lock(self, telegram_id: int) -> tuple[bool, int]:
        assert self._connection is not None
        cursor = await self._connection.execute(
            "SELECT attempts, locked_until FROM login_attempts WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return False, 0
        if row["locked_until"] > time.time():
            return True, int(row["locked_until"] - time.time())
        if row["locked_until"] > 0:
            await self.reset_login_attempts(telegram_id)
        return False, 0

    async def record_login_failure(
        self, telegram_id: int, max_attempts: int, lockout_duration: int,
    ) -> tuple[bool, int]:
        assert self._connection is not None
        cursor = await self._connection.execute(
            "SELECT attempts FROM login_attempts WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        attempts = (row["attempts"] + 1) if row else 1
        locked_until = 0.0
        now_locked = False
        if attempts >= max_attempts:
            locked_until = time.time() + lockout_duration
            attempts = 0
            now_locked = True
        await self._connection.execute(
            """
            INSERT INTO login_attempts (telegram_id, attempts, locked_until)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET attempts = ?, locked_until = ?
            """,
            (telegram_id, attempts, locked_until, attempts, locked_until),
        )
        await self._connection.commit()
        return now_locked, lockout_duration if now_locked else 0

    async def reset_login_attempts(self, telegram_id: int) -> None:
        assert self._connection is not None
        await self._connection.execute(
            "DELETE FROM login_attempts WHERE telegram_id = ?", (telegram_id,),
        )
        await self._connection.commit()

    # --- Audit ---

    async def log_audit(
        self, telegram_id: int, action: str, details: str | None = None,
    ) -> None:
        assert self._connection is not None
        now = datetime.now(timezone.utc).isoformat()
        await self._connection.execute(
            "INSERT INTO audit_log (telegram_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (telegram_id, action, details, now),
        )
        await self._connection.commit()

    async def get_audit_log(self, telegram_id: int, limit: int = 15) -> list[AuditEntry]:
        assert self._connection is not None
        cursor = await self._connection.execute(
            """
            SELECT id, telegram_id, action, details, created_at
            FROM audit_log WHERE telegram_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (telegram_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            AuditEntry(
                id=row["id"],
                telegram_id=row["telegram_id"],
                action=row["action"],
                details=row["details"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    @property
    def db_path(self) -> Path:
        return self._db_path

    async def get_stats(self) -> dict[str, int]:
        assert self._connection is not None
        users = await self._connection.execute("SELECT COUNT(*) as cnt FROM users")
        wallets = await self._connection.execute("SELECT COUNT(*) as cnt FROM wallets")
        user_row = await users.fetchone()
        wallet_row = await wallets.fetchone()
        return {
            "users": user_row["cnt"] if user_row else 0,
            "wallets": wallet_row["cnt"] if wallet_row else 0,
        }
