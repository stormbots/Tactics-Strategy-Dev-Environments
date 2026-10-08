"""Exercise the actual runtime selectors with synthetic APT output only."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
if not BASH and os.name == "nt":
    candidate = Path(r"C:\Program Files\Git\bin\bash.exe")
    if candidate.is_file():
        BASH = str(candidate)


@unittest.skipUnless(BASH, "Bash is required for the Linux runtime regression")
class NodeRuntimeSelection(unittest.TestCase):
    scripts = ("Install-SkyviewStudentDev.sh", "Update-SkyviewStudentDev.sh")

    def select(self, script, rows, package_exit=0):
        lines = (ROOT / "linux" / script).read_text().splitlines()
        position = next(i for i, line in enumerate(lines) if line.startswith("NODE_VERSION="))
        selector = "\n".join(lines[position:position + 2])
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "packages.txt"
            fixture.write_text(rows, encoding="utf-8", newline="\n")
            env = {**os.environ, "APT_FIXTURE": fixture.as_posix(), "APT_EXIT": str(package_exit)}
            # Mock only the package reader. Execute the selector and its real
            # no-candidate guard, never the provisioning script itself.
            program = """export PATH=/usr/bin:/bin
set -Eeuo pipefail
die() { printf '%s\\n' "$*" >&2; exit 1; }
apt-cache() {
  [[ "$*" == 'madison nodejs' ]] || exit 2
  cat "$APT_FIXTURE" || return $?
  return "$APT_EXIT"
}
""" + selector + '\nprintf "%s\\n" "$NODE_VERSION"\n'
            return subprocess.run([BASH, "--noprofile", "--norc", "-c", program],
                                  env=env, capture_output=True, text=True, timeout=15)

    def test_large_listing_preserves_first_approved_version_without_sigpipe(self):
        rows = ("nodejs | 26.0.0-1 | other-source\n"
                "nodejs | 24.21.0-1nodesource1 | node-source\n"
                "nodejs | 24.20.0-1nodesource1 | node-source\n")
        rows += "nodejs | 22.0.0-1 | other-source\n" * 100000
        for script in self.scripts:
            with self.subTest(script=script):
                result = self.select(script, rows)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "24.21.0-1nodesource1")

    def test_missing_approved_family_still_fails(self):
        for script in self.scripts:
            for rows in ("", "nodejs | 26.0.0-1 | other-source\n"):
                with self.subTest(script=script, rows=rows):
                    result = self.select(script, rows)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("No Node.js 24.x package", result.stderr)

    def test_package_reader_failure_is_not_ignored(self):
        for script in self.scripts:
            with self.subTest(script=script):
                result = self.select(script, "nodejs | 24.21.0-1 | source\n", package_exit=42)
                self.assertEqual(result.returncode, 42)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
