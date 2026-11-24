#!/usr/bin/env python3
"""Regression test: firmware ELF dependencies must not become XBPS dependencies."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCANNER = Path(__file__).with_name("elf-deps.py")

class ElfDepsTest(unittest.TestCase):
    def test_firmware_ignored_but_userspace_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / "stage"
            tools = root / "tools"
            tools.mkdir()
            # Synthetic AArch64 ELF header, with readelf mocked below.
            hdr = b"\x7fELF\x02\x01" + b"\0" * 12 + (183).to_bytes(2, "little")
            for name in ("usr/lib/firmware/qcom/sm8750/trustzone.mbn",
                         "lib/firmware/other.elf",
                         "usr/lib/modules/test.ko",
                         "usr/lib/linux-zhiyu/images/boot.img"):
                p = stage / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(hdr)
            for name, script in {
                "readelf": '#!/bin/sh\nprintf "%s\\n" " (NEEDED) Shared library: [libcmnlib.so]"\n',
                "xbps-query": "#!/bin/sh\nexit 0\n",
            }.items():
                p = tools / name
                p.write_text(script)
                p.chmod(0o755)
            env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"])
            def scan():
                return subprocess.run([sys.executable, str(SCANNER), str(stage)],
                                      env=env, text=True, capture_output=True)
            result = scan()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), ["", "", ""])
            # Do not suppress libcmnlib.so by name: a real userspace binary
            # needing it still has to fail.
            binary = stage / "usr/bin/test"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(hdr)
            result = scan()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("libcmnlib.so", result.stderr)
            self.assertIn("usr/bin/test", result.stderr)

if __name__ == "__main__":
    unittest.main()
