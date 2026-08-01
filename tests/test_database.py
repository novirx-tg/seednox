import tempfile
import unittest
from pathlib import Path

from src.crypto.kdf import generate_salt, hash_password
from src.database.repository import Repository


class TestDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_seednox.db"
        self.repo = Repository(self.db_path)
        await self.repo.connect()

    async def asyncTearDown(self):
        await self.repo.close()
        self.temp_dir.cleanup()

    async def test_user_creation_and_retrieval(self):
        user_id = 12345678
        salt = generate_salt()
        pw_hash = hash_password("TestPassword123!")

        created_user = await self.repo.create_user(
            telegram_id=user_id,
            password_hash=pw_hash,
            salt=salt,
        )

        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.telegram_id, user_id)
        self.assertEqual(created_user.password_hash, pw_hash)
        self.assertEqual(created_user.salt, salt)

        fetched_user = await self.repo.get_user(user_id)
        self.assertIsNotNone(fetched_user)
        self.assertEqual(fetched_user.telegram_id, user_id)
        self.assertEqual(fetched_user.salt, salt)

    async def test_wallet_crud_operations(self):
        user_id = 87654321
        salt = generate_salt()
        pw_hash = hash_password("TestPassword123!")
        await self.repo.create_user(telegram_id=user_id, password_hash=pw_hash, salt=salt)

        wallet = await self.repo.add_wallet(
            telegram_id=user_id,
            name="Main Vault",
            encrypted_seed=b"encrypted_seed_data_blob",
            encrypted_note=b"encrypted_note_blob",
            entry_type="seed",
        )
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.name, "Main Vault")
        self.assertEqual(wallet.encrypted_seed, b"encrypted_seed_data_blob")

        wallets = await self.repo.get_wallets(user_id)
        self.assertEqual(len(wallets), 1)
        self.assertEqual(wallets[0].name, "Main Vault")

        # Correct parameter order: (wallet_id, telegram_id)
        success = await self.repo.delete_wallet(wallet.id, user_id)
        self.assertTrue(success)

        wallets_after_delete = await self.repo.get_wallets(user_id)
        self.assertEqual(len(wallets_after_delete), 0)

    async def test_audit_logging(self):
        user_id = 11223344
        salt = generate_salt()
        pw_hash = hash_password("TestPassword123!")
        await self.repo.create_user(telegram_id=user_id, password_hash=pw_hash, salt=salt)

        await self.repo.log_audit(telegram_id=user_id, action="LOGIN", details="User logged in")
        stats = await self.repo.get_stats()
        self.assertGreaterEqual(stats["users"], 1)


if __name__ == "__main__":
    unittest.main()
