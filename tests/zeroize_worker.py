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
    # Generate random 32-byte secret canary as bytearray
    raw_canary = bytearray(secrets.token_bytes(32))
    canary_hex = raw_canary.hex()

    sm = SessionManager(timeout=300)
    user_id = 1337

    # Unlock session with secret
    sm.unlock(user_id, raw_canary)

    # Immediately wipe local raw_canary reference
    for i in range(len(raw_canary)):
        raw_canary[i] = 0
    del raw_canary
    gc.collect()

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
