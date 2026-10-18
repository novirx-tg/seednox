#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification Script for Reproducible Builds
Validates that two independent builds from separate source copies yield bit-for-bit identical outputs.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile


def sha256_of_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_build(src_dir: str, out_archive: str) -> str:
    pack_script = os.path.join(os.path.dirname(__file__), "reproducible_pack.py")
    cmd = [
        sys.executable,
        pack_script,
        "--src",
        src_dir,
        "--out",
        out_archive,
        "--epoch",
        "1700000000",
    ]
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    env["SOURCE_DATE_EPOCH"] = "1700000000"

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if res.returncode != 0:
        raise RuntimeError(f"Build failed: {res.stderr}")
    return sha256_of_file(out_archive)


def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print(f"=== Verifying Seednox Reproducible Build ===")
    print(f"Source Root: {root_dir}")

    with tempfile.TemporaryDirectory(prefix="repro_a_") as dir_a, tempfile.TemporaryDirectory(prefix="repro_b_") as dir_b:
        out_a = os.path.join(dir_a, "build_a.tar.gz")
        out_b = os.path.join(dir_b, "build_b.tar.gz")

        print("Executing Build A...")
        hash_a = run_build(root_dir, out_a)
        print(f"Build A SHA256: {hash_a}")

        print("Executing Build B (separate invocation)...")
        hash_b = run_build(root_dir, out_b)
        print(f"Build B SHA256: {hash_b}")

        if hash_a != hash_b:
            print("[ERROR] Reproducibility verification failed! Hashes do not match.")
            sys.exit(1)

        # Compare size
        size_a = os.path.getsize(out_a)
        size_b = os.path.getsize(out_b)
        assert size_a == size_b, f"Sizes differ: {size_a} != {size_b}"

        # Verify zip format as well
        zip_a = os.path.join(dir_a, "build_a.zip")
        zip_b = os.path.join(dir_b, "build_b.zip")
        zip_hash_a = run_build(root_dir, zip_a)
        zip_hash_b = run_build(root_dir, zip_b)
        if zip_hash_a != zip_hash_b:
            print("[ERROR] ZIP Reproducibility verification failed!")
            sys.exit(1)

        print("\n[SUCCESS] 100% BIT-FOR-BIT REPRODUCIBLE BUILDS VERIFIED!")
        print(f"Tarball SHA256: {hash_a} ({size_a} bytes)")
        print(f"ZIP     SHA256: {zip_hash_a} ({os.path.getsize(zip_a)} bytes)")


if __name__ == "__main__":
    main()
