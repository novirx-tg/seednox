import base64
import json
from datetime import datetime, timezone

from src.crypto import decrypt_seed, encrypt_seed

import struct

BACKUP_VERSION = 2
MAGIC_HEADER_V1 = b"SNX1"  # v1 заголовок (4 байта magic + 32 байта соль)
MAGIC_HEADER_V2 = b"SNX2"  # v2 заголовок (4 байта magic + 6 байт KDF params + 32 байта соль)
MAGIC_HEADER = MAGIC_HEADER_V2


def _encrypt_seed_with_argon_params(
    plaintext: str,
    password: str | bytes | bytearray,
    salt: bytes,
    time_cost: int,
    memory_cost: int,
    parallelism: int,
) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    from argon2 import low_level
    from src.crypto.kdf import generate_nonce

    secret_bytes = password.encode("utf-8") if isinstance(password, str) else bytes(password)
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
    nonce = generate_nonce()
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ciphertext


def create_encrypted_backup(
    wallets: list[dict],
    password: str | bytes | bytearray,
    salt: bytes,
    time_cost: int | None = None,
    memory_cost: int | None = None,
    parallelism: int | None = None,
) -> bytes:
    from src.config import get_settings
    s = get_settings()
    t_cost = time_cost if time_cost is not None else s.argon2_time_cost
    m_cost = memory_cost if memory_cost is not None else s.argon2_memory_cost
    p_par = parallelism if parallelism is not None else s.argon2_parallelism

    payload = {
        "version": BACKUP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "wallets": wallets,
    }
    plaintext = base64.b64encode(
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    ).decode("ascii")
    encrypted = _encrypt_seed_with_argon_params(
        plaintext, password, salt, t_cost, m_cost, p_par
    )
    # SNX2 Header: 4 bytes magic ("SNX2") + 6 bytes KDF (1B time_cost, 4B memory_cost, 1B parallelism) + 32 bytes salt
    kdf_meta = struct.pack(">BIB", t_cost, m_cost, p_par)
    return MAGIC_HEADER_V2 + kdf_meta + salt[:32] + encrypted


def _decrypt_seed_with_argon_params(
    encrypted_data: bytes,
    password: str | bytes | bytearray,
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

    secret_bytes = password.encode("utf-8") if isinstance(password, str) else bytes(password)
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
    password: str | bytes | bytearray,
    salt: bytes | None = None,
    candidate_salts: list[bytes] | None = None,
) -> dict:
    """
    Расшифровывает файл бэкапа .snx.
    - В формате SNX2 параметры KDF считываются прямо из заголовка (без перебора).
    - В формате SNX1 используется соль из файла и KDF-конфигурации.
    - В legacy-форматах без заголовка выполняется перебор солей и конфигураций.
    """
    # 0. Очистка от переносов строк и обработка возможного base64
    if not (data.startswith(MAGIC_HEADER_V2) or data.startswith(MAGIC_HEADER_V1)):
        try:
            stripped = data.strip()
            decoded = base64.b64decode(stripped)
            if len(decoded) >= 13:
                data = decoded
        except Exception:
            pass

    # 1. Формат SNX2 с встроенными KDF-метаданными (4B magic + 6B kdf + 32B salt = 42B)
    if data.startswith(MAGIC_HEADER_V2) and len(data) >= 42:
        t_cost, m_cost, p_par = struct.unpack(">BIB", data[4:10])
        embedded_salt = data[10:42]
        encrypted_payload = data[42:]
        plaintext = _decrypt_seed_with_argon_params(
            encrypted_payload, password, embedded_salt, t_cost, m_cost, p_par
        )
        decoded = base64.b64decode(plaintext.encode("ascii"))
        return json.loads(decoded.decode("utf-8"))

    # 2. Обратная совместимость с SNX1 (соль вшита, перебор только KDF параметров)
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

    if data.startswith(MAGIC_HEADER_V1) and len(data) > 36:
        embedded_salt = data[4:36]
        encrypted_payload = data[36:]
        last_exc = None
        for t_cost, m_cost, p_par in unique_argon:
            try:
                plaintext = _decrypt_seed_with_argon_params(
                    encrypted_payload, password, embedded_salt, t_cost, m_cost, p_par
                )
                decoded = base64.b64decode(plaintext.encode("ascii"))
                return json.loads(decoded.decode("utf-8"))
            except Exception as exc:
                last_exc = exc
        if last_exc:
            raise last_exc
        raise ValueError("Не удалось расшифровать бэкап SNX1: проверьте пароль")

    # 3. Перебор солей для старых бэкапов без magic-хэдера
    salts_to_try = []
    if salt:
        salts_to_try.append(salt)
    if candidate_salts:
        for s in candidate_salts:
            if s not in salts_to_try:
                salts_to_try.append(s)

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
