import re
from dataclasses import dataclass

from src.config import get_settings

# BIP39: 12, 15, 18, 21, 24 слова
VALID_WORD_COUNTS = {12, 15, 18, 21, 24}
WORD_PATTERN = re.compile(r"^[a-z]+$")


@dataclass
class ValidationResult:
    valid: bool
    error: str | None = None


def validate_password(password: str) -> ValidationResult:
    settings = get_settings()
    if len(password) < settings.min_password_length:
        return ValidationResult(
            False,
            f"Пароль должен быть не менее {settings.min_password_length} символов",
        )
    if len(password) > 128:
        return ValidationResult(False, "Пароль слишком длинный")
    if password.isascii() is False:
        return ValidationResult(False, "Пароль должен содержать только ASCII-символы")
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_upper and has_lower and has_digit):
        return ValidationResult(
            False,
            "Пароль должен содержать заглавные, строчные буквы и цифры",
        )
    return ValidationResult(True)


def validate_seed_phrase(seed: str) -> ValidationResult:
    words = seed.strip().lower().split()
    if not words:
        return ValidationResult(False, "Сид-фраза не может быть пустой")

    if len(words) not in VALID_WORD_COUNTS:
        return ValidationResult(
            False,
            f"Сид-фраза должна содержать {', '.join(map(str, sorted(VALID_WORD_COUNTS)))} слов",
        )

    for word in words:
        if not WORD_PATTERN.match(word):
            return ValidationResult(
                False,
                "Слова сид-фразы должны содержать только латинские буквы (a-z)",
            )
        if len(word) < 3 or len(word) > 8:
            return ValidationResult(False, f"Некорректное слово: {word[:3]}...")

    return ValidationResult(True)


def validate_wallet_name(name: str) -> ValidationResult:
    settings = get_settings()
    name = name.strip()
    if not name:
        return ValidationResult(False, "Название кошелька не может быть пустым")
    if len(name) > settings.max_wallet_name_length:
        return ValidationResult(
            False,
            f"Название не должно превышать {settings.max_wallet_name_length} символов",
        )
    if re.search(r"[\x00-\x1f]", name):
        return ValidationResult(False, "Название содержит недопустимые символы")
    return ValidationResult(True)
