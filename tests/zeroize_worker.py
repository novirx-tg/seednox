# -*- coding: utf-8 -*-
"""
Worker process for testing Zeroize in RAM via core dumps.
"""
import os
import sys
import gc
import secrets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.security.session import SessionManager

if __name__ == "__main__":
    # Generate random 32-byte secret canary directly into bytearray byte-by-byte.
    # Note: Using secrets.randbelow(256) ensures NO temporary 32-byte immutable 'bytes'
    # object is allocated on the CPython heap, preventing orphaned memory in pymalloc arenas.
    raw_canary = bytearray(32)
    for i in range(32):
        raw_canary[i] = secrets.randbelow(256)

    canary_hex = raw_canary.hex()

    sm = SessionManager(timeout=300)
    user_id = 1337

    # Unlock session with secret (UserSession takes ownership of raw_canary bytearray)
    sm.unlock(user_id, raw_canary)

    # Inform test: canary hex and ready for dump 1
    sys.stdout.write(f"CANARY:{canary_hex}\n")
    sys.stdout.write("READY_1\n")
    sys.stdout.flush()

    # Wait for LOCK command from parent test
    cmd = sys.stdin.readline().strip()
    if cmd == "LOCK":
        # Lock session: triggers zeroize() with 0x00 overwrite and gc.collect()
        sm.lock(user_id)
        gc.collect()

        sys.stdout.write("READY_2\n")
        sys.stdout.flush()

    # Wait for EXIT command
    cmd = sys.stdin.readline().strip()
    sys.exit(0)
