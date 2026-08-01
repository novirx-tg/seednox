import unittest
from src.config import Settings, get_settings


class TestConfig(unittest.TestCase):
    def test_settings_default_values(self):
        settings = get_settings()
        self.assertEqual(settings.session_timeout, 900)
        self.assertEqual(settings.max_password_attempts, 5)
        self.assertEqual(settings.argon2_time_cost, 3)

    def test_parse_allowed_user_ids_list(self):
        s = Settings(allowed_user_ids=[12345, 67890])
        self.assertEqual(s.allowed_user_ids, [12345, 67890])

    def test_parse_allowed_user_ids_str(self):
        s = Settings(allowed_user_ids="12345, 67890")
        self.assertEqual(s.allowed_user_ids, [12345, 67890])

    def test_parse_allowed_user_ids_empty(self):
        s = Settings(allowed_user_ids="")
        self.assertIsNone(s.allowed_user_ids)


if __name__ == "__main__":
    unittest.main()
