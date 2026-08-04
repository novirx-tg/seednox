"""
Headless-тесты для новых security-функций (без GUI и без Telegram):
* шифрование/расшифровка секретов с паролем-bytearray (затирание в памяти);
* MetaCipher: round-trip, обратная совместимость со старым открытым текстом;
* ленивая миграция названий и аудит-лога в репозитории;
* поиск и проверка уникальности по расшифрованным именам.

Запуск:  python tests/test_metadata_security.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Ускоряем Argon2 для теста (значения в пределах, разрешённых config.py).
os.environ.setdefault("ARGON2_MEMORY_COST", "16384")
os.environ.setdefault("ARGON2_TIME_COST", "2")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.crypto import decrypt_seed, encrypt_seed, generate_salt, hash_password, verify_password
from src.database.repository import Repository
from src.security.memory import SecretBytes, wipe
from src.security.metadata import MetaCipher, is_encrypted

PASSWORD = "correct horse battery staple 42"


def test_secret_bytes_and_wipe():
    buf = bytearray(b"super-secret-key")
    wipe(buf)
    assert buf == bytearray(len(buf)), "wipe должен занулить bytearray"

    box = SecretBytes("master-password")
    assert box.bytes() == b"master-password"
    box.wipe()
    assert box.wiped
    try:
        box.bytes()
        raise AssertionError("после wipe доступ должен падать")
    except ValueError:
        pass
    print("OK  memory: wipe/SecretBytes")


def test_encrypt_with_bytearray_password():
    salt = generate_salt()
    # пароль как bytearray (путь с затиранием памяти) должен работать так же, как str
    pw_ba = bytearray(PASSWORD.encode())
    enc = encrypt_seed("twelve words seed", pw_ba, salt)
    dec = decrypt_seed(enc, PASSWORD, salt)  # расшифровка обычной str-строкой
    assert dec == "twelve words seed"
    # verify_password тоже принимает bytearray
    h = hash_password(PASSWORD)
    assert verify_password(h, bytearray(PASSWORD.encode()))
    assert not verify_password(h, "wrong password")
    print("OK  crypto: пароль как bytearray эквивалентен str")


def test_metacipher_roundtrip_and_legacy():
    salt = generate_salt()
    meta = MetaCipher(PASSWORD, salt)

    enc = meta.encrypt("Ledger — 20 ETH")
    assert is_encrypted(enc) and enc != "Ledger — 20 ETH"
    assert meta.decrypt(enc) == "Ledger — 20 ETH"

    # разные вызовы → разный шифртекст (случайный nonce), но одинаковая расшифровка
    assert meta.encrypt("x") != meta.encrypt("x")

    # обратная совместимость: старый открытый текст возвращается как есть
    assert meta.decrypt("Old Plain Name") == "Old Plain Name"
    assert meta.decrypt(None) is None

    # неверный ключ не расшифрует
    other = MetaCipher(PASSWORD, generate_salt())
    try:
        other.decrypt(enc)
        raise AssertionError("чужой ключ не должен расшифровать")
    except Exception:
        pass

    meta.wipe()
    print("OK  metadata: MetaCipher round-trip + legacy passthrough")


async def _seed_legacy_db(repo: Repository, uid: int, salt: bytes):
    """Кладём в БД «старые» данные: имя записи и details аудита открытым текстом."""
    enc_seed = encrypt_seed("legacy seed phrase here", PASSWORD, salt)
    # add_wallet сохраняет name как передано → эмулируем legacy plaintext-имя
    await repo.add_wallet(uid, "Binance Main", enc_seed, None, "seed")
    await repo.log_audit(uid, "add_wallet", "Binance Main")


async def _run_repo_tests():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "vault_test.db"
        repo = Repository(db_path, encryption_key=None)
        await repo.connect()

        uid = 123456
        salt = generate_salt()
        await repo.create_user(uid, hash_password(PASSWORD), salt)

        await _seed_legacy_db(repo, uid, salt)

        meta = MetaCipher(PASSWORD, salt)

        # --- миграция названий ---
        migrated = await repo.encrypt_legacy_names(uid, meta)
        assert migrated == 1, f"ожидали 1 миграцию имени, получили {migrated}"
        migrated_again = await repo.encrypt_legacy_names(uid, meta)
        assert migrated_again == 0, "повторная миграция не должна ничего трогать (идемпотентность)"

        wallets = await repo.get_wallets(uid)
        assert len(wallets) == 1
        stored_name = wallets[0].name
        assert is_encrypted(stored_name), "имя в БД должно быть зашифровано"
        assert meta.decrypt(stored_name) == "Binance Main"
        # сам сид по-прежнему расшифровывается
        assert decrypt_seed(wallets[0].encrypted_seed, PASSWORD, salt) == "legacy seed phrase here"

        # --- миграция аудита ---
        amig = await repo.encrypt_legacy_audit(uid, meta)
        assert amig == 1
        entries = await repo.get_audit_log(uid)
        assert is_encrypted(entries[0].details)
        assert meta.decrypt(entries[0].details) == "Binance Main"

        # --- добавление новой записи с зашифрованным именем ---
        enc_seed2 = encrypt_seed("second seed", PASSWORD, salt)
        await repo.add_wallet(uid, meta.encrypt("Ledger Cold"), enc_seed2, None, "seed")

        wallets = await repo.get_wallets(uid)
        names = sorted(meta.decrypt(w.name) for w in wallets)
        assert names == ["Binance Main", "Ledger Cold"], names

        # --- поиск в памяти по расшифрованному имени ---
        term = "ledger"
        found = [w for w in wallets if term.lower() in (meta.decrypt(w.name) or "").lower()]
        assert len(found) == 1 and meta.decrypt(found[0].name) == "Ledger Cold"

        # --- проверка уникальности по расшифрованному имени (регистронезависимо) ---
        existing = {(meta.decrypt(w.name) or "").strip().lower() for w in wallets}
        assert "binance main" in existing  # дубликат должен отлавливаться на уровне приложения

        await repo.close()
    print("OK  repository: миграция имён/аудита, поиск, уникальность")


def main():
    test_secret_bytes_and_wipe()
    test_encrypt_with_bytearray_password()
    test_metacipher_roundtrip_and_legacy()
    asyncio.run(_run_repo_tests())
    print("\n[PASS] Все тесты security-функций пройдены")


if __name__ == "__main__":
    main()
