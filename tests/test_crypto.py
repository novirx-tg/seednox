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


if __name__ == "__main__":
    unittest.main()
