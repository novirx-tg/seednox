# -*- coding: utf-8 -*-
"""
Integration test for Zeroize RAM Verification via Memory Dumps (gcore on Linux / MiniDump on Windows).
Validates that sensitive secrets are physically erased from process memory after session lock.
"""

import os
import sys
import subprocess
import tempfile
import unittest
import platform


class TestZeroizeCoreDump(unittest.TestCase):

    def test_zeroize_process_memory_dump(self):
        worker_script = os.path.join(os.path.dirname(__file__), "zeroize_worker.py")

        proc = subprocess.Popen(
            [sys.executable, worker_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                # 1. Read canary info from worker
                canary_line = proc.stdout.readline().strip()
                if not canary_line.startswith("CANARY:"):
                    err = proc.stderr.read()
                    self.fail(f"Worker process failed to start: {err}")

                canary_hex = canary_line.split("CANARY:", 1)[1]
                canary_bytes = bytes.fromhex(canary_hex)

                ready_1 = proc.stdout.readline().strip()
                self.assertEqual(ready_1, "READY_1")

                pid = proc.pid
                dump_1_file = os.path.join(tmp_dir, "dump_before.bin")
                dump_2_file = os.path.join(tmp_dir, "dump_after.bin")

                # Create memory dump 1 (while session is unlocked)
                dumped_1 = self._dump_process_memory(pid, dump_1_file)
                if not dumped_1:
                    self.skipTest("Memory dumping is not supported or permitted on this test runner environment")

                # Verify canary secret is present in memory dump 1
                with open(dump_1_file, "rb") as f:
                    content_1 = f.read()

                occurrences_before = content_1.count(canary_bytes)
                self.assertGreater(
                    occurrences_before,
                    0,
                    "Canary secret must be present in process memory dump while session is unlocked",
                )

                # 2. Send LOCK command to trigger zeroize()
                proc.stdin.write("LOCK\n")
                proc.stdin.flush()

                ready_2 = proc.stdout.readline().strip()
                self.assertEqual(ready_2, "READY_2")

                # Create memory dump 2 (after session lock)
                dumped_2 = self._dump_process_memory(pid, dump_2_file)
                self.assertTrue(dumped_2, "Failed to create second memory dump after lock")

                # Verify canary secret is completely absent from memory dump 2
                with open(dump_2_file, "rb") as f:
                    content_2 = f.read()

                occurrences_after = content_2.count(canary_bytes)
                self.assertEqual(
                    occurrences_after,
                    0,
                    f"ZEROIZE FAILED: Canary secret found {occurrences_after} time(s) in process memory dump after lock!",
                )

            finally:
                try:
                    proc.stdin.write("EXIT\n")
                    proc.stdin.flush()
                except Exception:
                    pass
                for stream in [proc.stdin, proc.stdout, proc.stderr]:
                    if stream:
                        try:
                            stream.close()
                        except Exception:
                            pass
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    pass

    def _dump_process_memory(self, pid: int, out_file: str) -> bool:
        system = platform.system().lower()

        # 1. Linux: gcore
        if system == "linux":
            try:
                prefix = out_file + "_prefix"
                res = subprocess.run(
                    ["gcore", "-o", prefix, str(pid)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=15,
                )
                if res.returncode == 0:
                    created_file = f"{prefix}.{pid}"
                    if os.path.exists(created_file):
                        import shutil
                        shutil.move(created_file, out_file)
                        return True
            except Exception:
                pass

        # 2. Windows: MiniDumpWriteDump via ctypes
        elif system == "windows":
            try:
                import ctypes
                from ctypes import wintypes

                MiniDumpWithFullMemory = 0x00000002
                PROCESS_ALL_ACCESS = 0x1F0FFF

                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                dbghelp = ctypes.WinDLL("dbghelp", use_last_error=True)

                dbghelp.MiniDumpWriteDump.argtypes = [
                    wintypes.HANDLE, wintypes.DWORD, wintypes.HANDLE, wintypes.DWORD,
                    wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID
                ]
                dbghelp.MiniDumpWriteDump.restype = wintypes.BOOL

                kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel32.OpenProcess.restype = wintypes.HANDLE

                h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
                if not h_process:
                    return False

                try:
                    GENERIC_WRITE = 0x40000000
                    CREATE_ALWAYS = 2
                    FILE_ATTRIBUTE_NORMAL = 0x80

                    kernel32.CreateFileW.argtypes = [
                        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
                    ]
                    kernel32.CreateFileW.restype = wintypes.HANDLE

                    h_file = kernel32.CreateFileW(
                        out_file,
                        GENERIC_WRITE,
                        0,
                        None,
                        CREATE_ALWAYS,
                        FILE_ATTRIBUTE_NORMAL,
                        None,
                    )
                    if h_file == wintypes.HANDLE(-1).value or h_file == -1:
                        return False

                    try:
                        success = dbghelp.MiniDumpWriteDump(
                            h_process,
                            pid,
                            h_file,
                            MiniDumpWithFullMemory,
                            None,
                            None,
                            None,
                        )
                        return bool(success)
                    finally:
                        kernel32.CloseHandle(h_file)
                finally:
                    kernel32.CloseHandle(h_process)
            except Exception:
                return False

        return False


if __name__ == "__main__":
    unittest.main()
