#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seednox Reproducible Packaging Utility
Produces bit-for-bit identical archives regardless of filesystem, build time, or user.
Adheres to reproducible-builds.org standards:
- Fixed SOURCE_DATE_EPOCH timestamps
- Deterministic lexicographical file ordering
- Normalized file permissions and ownership (uid=0, gid=0)
- Zero gzip header timestamps (mtime=0)
"""

import argparse
import gzip
import io
import os
import sys
import tarfile
import zipfile
import hashlib

# Default epoch: 2023-11-14 22:13:20 UTC if not set in environment
DEFAULT_EPOCH = 1700000000

EXCLUDE_PATTERNS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".hypothesis",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "venv",
    ".venv",
    "temp",
    "tmp",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".tmp",
    ".bin",
}


def get_source_date_epoch() -> int:
    epoch_str = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch_str:
        try:
            return int(epoch_str)
        except ValueError:
            pass
    return DEFAULT_EPOCH


def should_include(rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts:
        if part in EXCLUDE_PATTERNS or part.startswith("."):
            return False
    _, ext = os.path.splitext(rel_path)
    if ext.lower() in EXCLUDE_EXTENSIONS:
        return False
    return True


def collect_files(root_dir: str) -> list[str]:
    included = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Sort in-place for deterministic traversal
        dirnames.sort()
        filenames.sort()
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            rel_path = os.path.relpath(full_path, root_dir)
            if should_include(rel_path):
                included.append(rel_path)
    included.sort()
    return included


def create_reproducible_tar_gz(root_dir: str, out_path: str, epoch: int) -> str:
    files = collect_files(root_dir)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    # We write tar content into in-memory buffer, then gzip with mtime=0 for bit-for-bit reproducibility
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w", dereference=False) as tf:
        for rel_path in files:
            full_path = os.path.join(root_dir, rel_path)
            norm_rel_path = rel_path.replace("\\", "/")
            
            with open(full_path, "rb") as f:
                content = f.read()

            ti = tarfile.TarInfo(name=f"seednox/{norm_rel_path}")
            ti.size = len(content)
            ti.mtime = epoch
            ti.mode = 0o644
            ti.uid = 0
            ti.gid = 0
            ti.uname = "root"
            ti.gname = "root"
            ti.type = tarfile.REGTYPE

            tf.addfile(ti, io.BytesIO(content))

    tar_bytes = tar_buf.getvalue()

    # Gzip with explicit mtime to prevent host timestamp embedding
    gz_buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=gz_buf, mtime=0) as gz:
        gz.write(tar_bytes)

    out_bytes = gz_buf.getvalue()
    with open(out_path, "wb") as f:
        f.write(out_bytes)

    sha256 = hashlib.sha256(out_bytes).hexdigest()
    return sha256


def create_reproducible_zip(root_dir: str, out_path: str, epoch: int) -> str:
    import datetime
    dt = datetime.datetime.fromtimestamp(epoch, tz=datetime.timezone.utc)
    zip_time = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    files = collect_files(root_dir)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path in files:
            full_path = os.path.join(root_dir, rel_path)
            norm_rel_path = rel_path.replace("\\", "/")

            with open(full_path, "rb") as f:
                content = f.read()

            zinfo = zipfile.ZipInfo(filename=f"seednox/{norm_rel_path}", date_time=zip_time)
            zinfo.external_attr = 0o644 << 16
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zinfo, content)

    out_bytes = zip_buf.getvalue()
    with open(out_path, "wb") as f:
        f.write(out_bytes)

    sha256 = hashlib.sha256(out_bytes).hexdigest()
    return sha256


def main():
    parser = argparse.ArgumentParser(description="Deterministic reproducible archive packager")
    parser.add_argument("--src", default=".", help="Source directory (default: current dir)")
    parser.add_argument("--out", default="dist/seednox-1.0.3-reproducible.tar.gz", help="Output path")
    parser.add_argument("--epoch", type=int, default=None, help="SOURCE_DATE_EPOCH override")
    args = parser.parse_args()

    epoch = args.epoch if args.epoch is not None else get_source_date_epoch()
    out_path = args.out

    if out_path.endswith(".zip"):
        sha256 = create_reproducible_zip(args.src, out_path, epoch)
    else:
        sha256 = create_reproducible_tar_gz(args.src, out_path, epoch)

    checksum_file = f"{out_path}.sha256"
    with open(checksum_file, "w", encoding="utf-8") as f:
        f.write(f"{sha256}  {os.path.basename(out_path)}\n")

    print(f"Reproducible build successful:")
    print(f"  Artifact: {out_path}")
    print(f"  SHA256:   {sha256}")
    print(f"  Checksum: {checksum_file}")


if __name__ == "__main__":
    main()
