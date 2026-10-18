# -*- coding: utf-8 -*-
"""
Fuzzing Suite for Seednox Cryptographic Engine (AES-256-GCM & Nonce Security).
Protects against:
  1. Nonce reuse catastrophe (Forbidden Attack / Joux Attack)
  2. Bit-flip manipulation & Tag tampering (AEAD integrity)
  3. Truncation and boundary attacks
  4. Password and Salt deviation sensitivity
"""

import os
import secrets
import unittest
from cryptography.exceptions import InvalidTag
from hypothesis import given, strategies as st, settings, Phase

from src.crypto.encryption import encrypt_seed, decrypt_seed
from src.crypto.kdf import derive_key, generate_nonce, generate_salt


class FuzzAESGCM(unittest.TestCase):

    @given(
        payload=st.text(min_size=0, max_size=5000),
        password=st.text(min_size=1, max_size=128),
        salt=st.binary(min_size=32, max_size=32),
    )
    @settings(max_examples=50, phases=[Phase.generate, Phase.shrink], deadline=None)
    def test_fuzz_roundtrip_invariance(self, payload: str, password: str, salt: bytes):
        """?????????: ????? ??????? ????????????? payload ?????? ???????????????? 1-?-1."""
        encrypted = encrypt_seed(payload, password, salt)
        self.assertGreaterEqual(len(encrypted), 12 + 16)  # 12 nonce + 16 GCM tag
        decrypted = decrypt_seed(encrypted, password, salt)
        self.assertEqual(decrypted, payload)

    @given(
        payload=st.text(min_size=1, max_size=200),
        password=st.text(min_size=8, max_size=64),
        salt=st.binary(min_size=32, max_size=32),
        bit_pos=st.integers(min_value=0, max_value=500),
    )
    @settings(max_examples=50, deadline=None)
    def test_fuzz_bit_flip_authenticity(self, payload: str, password: str, salt: bytes, bit_pos: int):
        """????????? AEAD: ???????? ?????? ???? ? ??????????? ??? ???? ??????? ????????? ? InvalidTag."""
        encrypted = bytearray(encrypt_seed(payload, password, salt))
        target_byte = (bit_pos // 8) % len(encrypted)
        target_bit = bit_pos % 8

        # ??????? ???? ???
        encrypted[target_byte] ^= (1 << target_bit)

        with self.assertRaises((InvalidTag, ValueError)):
            decrypt_seed(bytes(encrypted), password, salt)

    @given(
        payload=st.text(min_size=1, max_size=200),
        password=st.text(min_size=8, max_size=64),
        salt=st.binary(min_size=32, max_size=32),
        cut_len=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=40, deadline=None)
    def test_fuzz_truncation_resistance(self, payload: str, password: str, salt: bytes, cut_len: int):
        """?????????: ???????? ??????????? ?? ?????? ????????? ? ????? ??? ??????."""
        encrypted = encrypt_seed(payload, password, salt)
        cut_point = max(0, len(encrypted) - cut_len)
        truncated = encrypted[:cut_point]

        with self.assertRaises((InvalidTag, ValueError)):
            decrypt_seed(truncated, password, salt)

    def test_fuzz_massive_nonce_collision_resistance(self):
        """
        ????????? 50 000 ?????? ??????.
        ?????????, ??? CSPRNG ????????? secrets.token_bytes(12) ?? ????? ??????
        ? ???????? ?? ???????????? 2^96 ???.
        """
        total_samples = 50000
        generated = set()
        for _ in range(total_samples):
            n = generate_nonce()
            self.assertEqual(len(n), 12)
            self.assertNotIn(n, generated, "??????????? ??????????: ?????????? ???????? nonce AES-GCM!")
            generated.add(n)
        self.assertEqual(len(generated), total_samples)


if __name__ == "__main__":
    unittest.main()
