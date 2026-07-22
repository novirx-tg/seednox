from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    telegram_id: int
    password_hash: str
    salt: bytes
    created_at: datetime
    pin_hash: str | None = None
    pin_enabled: bool = False
    duress_password_hash: str | None = None
    risk_accepted_at: datetime | None = None


@dataclass
class Wallet:
    id: int
    telegram_id: int
    name: str
    encrypted_seed: bytes
    created_at: datetime
    updated_at: datetime
    encrypted_note: bytes | None = None


@dataclass
class DecoyWallet:
    id: int
    telegram_id: int
    name: str
    encrypted_seed: bytes
    created_at: datetime
    updated_at: datetime
    encrypted_note: bytes | None = None


@dataclass
class AuditEntry:
    id: int
    telegram_id: int
    action: str
    details: str | None
    created_at: datetime
