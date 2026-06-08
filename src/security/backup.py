import base64
import json
from datetime import datetime, timezone

from src.crypto import decrypt_seed, encrypt_seed

BACKUP_VERSION = 1


def create_encrypted_backup(
    wallets: list[dict],
    password: str,
    salt: bytes,
) -> bytes:
    payload = {
        "version": BACKUP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "wallets": wallets,
    }
    plaintext = base64.b64encode(
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    ).decode("ascii")
    return encrypt_seed(plaintext, password, salt)


def decrypt_backup_file(data: bytes, password: str, salt: bytes) -> dict:
    plaintext = decrypt_seed(data, password, salt)
    decoded = base64.b64decode(plaintext.encode("ascii"))
    return json.loads(decoded.decode("utf-8"))


def wallet_to_backup_item(
    name: str,
    encrypted_seed: bytes,
    encrypted_note: bytes | None,
) -> dict:
    return {
        "name": name,
        "encrypted_seed": encrypted_seed.hex(),
        "encrypted_note": encrypted_note.hex() if encrypted_note else None,
    }


def backup_item_to_bytes(item: dict) -> tuple[str, bytes, bytes | None]:
    note = bytes.fromhex(item["encrypted_note"]) if item.get("encrypted_note") else None
    return item["name"], bytes.fromhex(item["encrypted_seed"]), note
