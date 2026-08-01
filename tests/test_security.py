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

        valid_seed_res = validate_seed_phrase("word " * 12)
        self.assertTrue(valid_seed_res.valid)
        self.assertIsNone(valid_seed_res.error)

        invalid_seed_res = validate_seed_phrase("short seed")
        self.assertFalse(invalid_seed_res.valid)
        self.assertIsNotNone(invalid_seed_res.error)


if __name__ == "__main__":
    unittest.main()
