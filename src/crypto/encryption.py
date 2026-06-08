from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .kdf import derive_key, generate_nonce


def encrypt_seed(seed_phrase: str, password: str, salt: bytes) -> bytes:
    """
    Шифрует сид-фразу AES-256-GCM.
    Формат: nonce (12) + ciphertext + tag (включён в ciphertext GCM).
    """
    key = derive_key(password, salt)
    nonce = generate_nonce()
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, seed_phrase.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt_seed(encrypted_data: bytes, password: str, salt: bytes) -> str:
    """Расшифровывает сид-фразу. Выбрасывает исключение при неверном пароле."""
    if len(encrypted_data) < 13:
        raise ValueError("Некорректные зашифрованные данные")

    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
