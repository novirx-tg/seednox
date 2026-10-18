import unittest
from cryptography.exceptions import InvalidTag

from src.crypto.encryption import decrypt_seed, encrypt_seed
from src.crypto.kdf import (
    derive_key,
    generate_nonce,
    generate_salt,
    hash_password,
    verify_password,
)


class TestCrypto(unittest.TestCase):
    def test_salt_and_nonce_generation(self):
        salt1 = generate_salt()
        salt2 = generate_salt()
        self.assertEqual(len(salt1), 32)
        self.assertEqual(len(salt2), 32)
        self.assertNotEqual(salt1, salt2)

        nonce1 = generate_nonce()
        nonce2 = generate_nonce()
        self.assertEqual(len(nonce1), 12)
        self.assertEqual(len(nonce2), 12)
        self.assertNotEqual(nonce1, nonce2)

    def test_password_hashing_and_verification(self):
        password = "CorrectHorseBatteryStaple123!"
        password_hash = hash_password(password)

        self.assertNotEqual(password_hash, password)
        self.assertTrue(verify_password(password_hash, password))
        self.assertFalse(verify_password(password_hash, "WrongPassword123!"))

    def test_derive_key_determinism(self):
        password = "MasterPassword123!"
        salt = generate_salt()

        key1 = derive_key(password, salt)
        key2 = derive_key(password, salt)
        self.assertEqual(len(key1), 32)
        self.assertEqual(key1, key2)

        key_different_salt = derive_key(password, generate_salt())
        self.assertNotEqual(key1, key_different_salt)

    def test_encrypt_and_decrypt_seed_success(self):
        seed_phrase = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        password = "StrongMasterPassword987!"
        salt = generate_salt()

        encrypted = encrypt_seed(seed_phrase, password, salt)
        self.assertGreater(len(encrypted), 12)
        self.assertNotEqual(encrypted, seed_phrase.encode("utf-8"))

        decrypted = decrypt_seed(encrypted, password, salt)
        self.assertEqual(decrypted, seed_phrase)

    def test_decrypt_seed_wrong_password_fails(self):
        seed_phrase = "test seed phrase secret 123"
        password = "RealPassword123!"
        wrong_password = "FakePassword123!"
        salt = generate_salt()

        encrypted = encrypt_seed(seed_phrase, password, salt)

        with self.assertRaises(InvalidTag):
            decrypt_seed(encrypted, wrong_password, salt)

    def test_decrypt_seed_invalid_data(self):
        password = "RealPassword123!"

        with self.assertRaises(ValueError):
            decrypt_seed(b"short", password, generate_salt())

    def test_derive_key_and_encryption_with_bytearray(self):
        password_str = "CorrectHorseBytearray123!"
        password_ba = bytearray(password_str.encode("utf-8"))
        salt = generate_salt()

        key_str = derive_key(password_str, salt)
        key_ba = derive_key(password_ba, salt)
        self.assertEqual(key_str, key_ba)

        seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        encrypted = encrypt_seed(seed, password_ba, salt)
        decrypted = decrypt_seed(encrypted, password_ba, salt)
        self.assertEqual(decrypted, seed)

    def test_backup_snx2_and_backward_compatibility(self):
        from src.security.backup import create_encrypted_backup, decrypt_backup_file, MAGIC_HEADER_V2, MAGIC_HEADER_V1
        wallets = [{"name": "Test Wallet", "encrypted_seed": "abcd", "encrypted_note": None}]
        password = "BackupSuperPassword777!"
        salt = generate_salt()

        # Тест SNX2 создания и мгновенной расшифровки
        backup_snx2 = create_encrypted_backup(wallets, password, salt)
        self.assertTrue(backup_snx2.startswith(MAGIC_HEADER_V2))
        self.assertGreaterEqual(len(backup_snx2), 42)

        restored_snx2 = decrypt_backup_file(backup_snx2, password)
        self.assertEqual(len(restored_snx2["wallets"]), 1)
        self.assertEqual(restored_snx2["wallets"][0]["name"], "Test Wallet")

        # Тест обратной совместимости с SNX1
        import base64, json
        from datetime import datetime, timezone
        payload = {"version": 1, "exported_at": datetime.now(timezone.utc).isoformat(), "wallets": wallets}
        plaintext = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        encrypted_snx1 = encrypt_seed(plaintext, password, salt)
        backup_snx1 = MAGIC_HEADER_V1 + salt[:32] + encrypted_snx1

        restored_snx1 = decrypt_backup_file(backup_snx1, password)
        self.assertEqual(len(restored_snx1["wallets"]), 1)
        self.assertEqual(restored_snx1["wallets"][0]["name"], "Test Wallet")

    def test_nonce_uniqueness_and_no_reuse(self):
        """Проверка невозможности коллизии nonce (AES-GCM nonce reuse catastrophe)."""
        seen_nonces = set()
        count = 10000
        for _ in range(count):
            nonce = generate_nonce()
            self.assertEqual(len(nonce), 12)
            self.assertNotIn(nonce, seen_nonces)
            seen_nonces.add(nonce)
        self.assertEqual(len(seen_nonces), count)

        # Проверяем, что encrypt_seed всегда использует свежий уникальный nonce
        payload = "seednox ultra secret seed phrase"
        password = "MasterPassword123!"
        salt = generate_salt()
        encryption_nonces = set()
        for _ in range(30):
            ciphertext = encrypt_seed(payload, password, salt)
            nonce = ciphertext[:12]
            self.assertNotIn(nonce, encryption_nonces)
            encryption_nonces.add(nonce)
        self.assertEqual(len(encryption_nonces), 30)


if __name__ == "__main__":
    unittest.main()
