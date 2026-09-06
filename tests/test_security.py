import time
import unittest

from src.security.password_strength import check_password_strength, format_strength
from src.security.rate_limiter import RateLimiter
from src.security.session import SessionManager
from src.security.validators import validate_seed_phrase, validate_wallet_name


class TestSecurity(unittest.TestCase):
    def test_rate_limiter(self):
        limiter = RateLimiter(max_attempts=3, lockout_duration=60)
        user_id = 12345

        locked, remaining = limiter.is_locked(user_id)
        self.assertFalse(locked)
        self.assertEqual(remaining, 0)

        is_now_locked, duration = limiter.record_failure(user_id)
        self.assertFalse(is_now_locked)

        is_now_locked, duration = limiter.record_failure(user_id)
        self.assertFalse(is_now_locked)

        is_now_locked, duration = limiter.record_failure(user_id)
        self.assertTrue(is_now_locked)
        self.assertEqual(duration, 60)

        locked, remaining = limiter.is_locked(user_id)
        self.assertTrue(locked)
        self.assertGreater(remaining, 0)

        limiter.reset(user_id)
        locked, remaining = limiter.is_locked(user_id)
        self.assertFalse(locked)

    def test_session_manager_lifecycle(self):
        sm = SessionManager(timeout=2)
        user_id = 999
        pw = "SuperSecretPassword123!"

        sm.unlock(user_id, pw)
        self.assertTrue(sm.is_unlocked(user_id))
        self.assertEqual(sm.get_password(user_id), pw)

        time.sleep(2.1)
        self.assertFalse(sm.is_unlocked(user_id))
        self.assertIsNone(sm.get_password(user_id))

    def test_password_strength_checker(self):
        weak = check_password_strength("12345")
        self.assertFalse(weak.acceptable)

        strong = check_password_strength("CorrectHorseBatteryStaple2026!#")
        self.assertTrue(strong.acceptable)
        self.assertIn("Надёжность:", format_strength("CorrectHorseBatteryStaple2026!#"))

    def test_validators(self):
        valid_name_res = validate_wallet_name("My Ledger Seed")
        self.assertTrue(valid_name_res.valid)
        self.assertIsNone(valid_name_res.error)

        invalid_name_res = validate_wallet_name("")
        self.assertFalse(invalid_name_res.valid)
        self.assertIsNotNone(invalid_name_res.error)

        valid_seed_12 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        valid_seed_res = validate_seed_phrase(valid_seed_12)
        self.assertTrue(valid_seed_res.valid)
        self.assertIsNone(valid_seed_res.error)

        # 24-словная валидная мнемоника BIP-39
        valid_seed_24 = "legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth title"
        valid_24_res = validate_seed_phrase(valid_seed_24)
        self.assertTrue(valid_24_res.valid)
        self.assertIsNone(valid_24_res.error)

        # Неверная длина
        invalid_len_res = validate_seed_phrase("short seed phrase")
        self.assertFalse(invalid_len_res.valid)
        self.assertIsNotNone(invalid_len_res.error)

        # Несуществующее слово
        invalid_word_res = validate_seed_phrase("abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abracadabra")
        self.assertFalse(invalid_word_res.valid)
        self.assertIn("не найдено в словаре", invalid_word_res.error)

        # Нарушенная контрольная сумма
        invalid_checksum_res = validate_seed_phrase("abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon")
        self.assertFalse(invalid_checksum_res.valid)
        self.assertIn("контрольная сумма", invalid_checksum_res.error)

    def test_session_zeroize(self):
        sm = SessionManager(timeout=60)
        user_id = 777
        pw = "TestPasswordBytearray123!"

        sm.unlock(user_id, pw)
        pw_bytes = sm.get_password_bytes(user_id)
        self.assertIsNotNone(pw_bytes)
        self.assertEqual(pw_bytes.decode("utf-8"), pw)

        # Блокируем сессию и проверяем, что bytearray затерт нулями
        sm.lock(user_id)
        self.assertFalse(sm.is_unlocked(user_id))
        self.assertIsNone(sm.get_password(user_id))
        # Проверяем, что исходный буфер затерт
        self.assertEqual(len(pw_bytes), 0)


if __name__ == "__main__":
    unittest.main()
