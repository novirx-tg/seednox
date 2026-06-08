import os
import secrets

from argon2 import PasswordHasher, low_level
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from src.config import get_settings


def _hasher() -> PasswordHasher:
    s = get_settings()
    return PasswordHasher(
        time_cost=s.argon2_time_cost,
        memory_cost=s.argon2_memory_cost,
        parallelism=s.argon2_parallelism,
        hash_len=32,
        salt_len=16,
    )


def generate_salt() -> bytes:
    return os.urandom(32)


def hash_password(password: str) -> str:
    """Хеширует мастер-пароль для верификации (не для шифрования)."""
    return _hasher().hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    hasher = _hasher()
    try:
        hasher.verify(password_hash, password)
        if hasher.check_needs_rehash(password_hash):
            return True
        return True
    except VerifyMismatchError:
        return False


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Деривация ключа шифрования из пароля и соли.
    Argon2id → HKDF-SHA256 → 32-байтный AES-ключ.
    """
    s = get_settings()
    raw_key = low_level.hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt[:16],
        time_cost=s.argon2_time_cost,
        memory_cost=s.argon2_memory_cost,
        parallelism=s.argon2_parallelism,
        hash_len=32,
        type=low_level.Type.ID,
    )
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"seednox-v1-encryption",
    )
    return hkdf.derive(raw_key)


def generate_nonce() -> bytes:
    return secrets.token_bytes(12)
