import base64
import json
from datetime import datetime, timezone

from src.crypto import decrypt_seed, encrypt_seed

BACKUP_VERSION = 1
MAGIC_HEADER = b"SNX1"  # 4-байтовый заголовок для портативных бэкапов с встроенной солью


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
    encrypted = encrypt_seed(plaintext, password, salt)
    # Префиксуем маджик-хэдером и солью (32 байта) для портативного переноса
    return MAGIC_HEADER + salt[:32] + encrypted


def _decrypt_seed_with_argon_params(
    encrypted_data: bytes,
    password: str,
    salt: bytes,
    time_cost: int,
    memory_cost: int,
    parallelism: int,
) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    from argon2 import low_level

    if len(encrypted_data) < 13:
        raise ValueError("Некорректные данные")

    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]

    secret_bytes = bytes(password) if isinstance(password, (bytes, bytearray)) else password.encode("utf-8")
    raw_key = low_level.hash_secret_raw(
        secret=secret_bytes,
        salt=salt[:16],
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_len=32,
        type=low_level.Type.ID,
    )
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"seednox-v1-encryption",
    )
    key = hkdf.derive(raw_key)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def decrypt_backup_file(
    data: bytes,
    password: str,
    salt: bytes | None = None,
    candidate_salts: list[bytes] | None = None,
) -> dict:
    """
    Расшифровывает файл бэкапа .snx.
    Поддерживает новые портативные файлы (с SNX1-хэдером и встроенной солью),
    а также старые бэкапы через перебор солей и параметров Argon2 KDF.
    """
    # 0. Очистка от переносов строк и обработка возможного base64
    if not data.startswith(MAGIC_HEADER):
        try:
            stripped = data.strip()
            decoded = base64.b64decode(stripped)
            if len(decoded) >= 13:
                data = decoded
        except Exception:
            pass

    # 1. Проверяем портативный заголовок SNX1
    if data.startswith(MAGIC_HEADER) and len(data) > 36:
        embedded_salt = data[4:36]
        encrypted_payload = data[36:]
        plaintext = decrypt_seed(encrypted_payload, password, embedded_salt)
        decoded = base64.b64decode(plaintext.encode("ascii"))
        return json.loads(decoded.decode("utf-8"))

    # 2. Перебор солей для старых бэкапов
    salts_to_try = []
    if salt:
        salts_to_try.append(salt)
    if candidate_salts:
        for s in candidate_salts:
            if s not in salts_to_try:
                salts_to_try.append(s)

    # Варианты конфигурации Argon2 KDF
    from src.config import get_settings
    s_curr = get_settings()
    argon_configs = [
        (s_curr.argon2_time_cost, s_curr.argon2_memory_cost, s_curr.argon2_parallelism),
        (3, 65536, 4),
        (2, 65536, 4),
        (2, 19456, 1),
        (3, 32768, 2),
    ]
    unique_argon = []
    for cfg in argon_configs:
        if cfg not in unique_argon:
            unique_argon.append(cfg)

    last_exc = None
    for s in salts_to_try:
        for t_cost, m_cost, p_par in unique_argon:
            try:
                plaintext = _decrypt_seed_with_argon_params(data, password, s, t_cost, m_cost, p_par)
                decoded = base64.b64decode(plaintext.encode("ascii"))
                return json.loads(decoded.decode("utf-8"))
            except Exception as exc:
                last_exc = exc

    if last_exc:
        raise last_exc
    raise ValueError("Не удалось расшифровать бэкап: проверьте пароль")


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
