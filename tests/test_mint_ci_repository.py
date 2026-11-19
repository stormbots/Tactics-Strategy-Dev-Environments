"""Exercise bounded CI transport changes without modifying host APT settings."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

from mint_ci_repository import repository_bytes


class Repository(unittest.TestCase):
    source = b"deb http://packages.linuxmint.com zena main upstream import backport\n"

    def test_preserves_other_repositories_comments_and_line_endings(self):
        before = (b"# Default packages.linuxmint.com retained in comment\r\n" +
                  self.source.replace(b"\n", b"\r\n") +
                  b"deb http://archive.ubuntu.com/ubuntu noble main restricted universe multiverse\n" +
                  b"deb http://security.ubuntu.com/ubuntu/ noble-security main\n")
        expected = before.replace(b"deb http://packages.linuxmint.com", b"deb https://fastly.linuxmint.io")
        self.assertEqual(repository_bytes(before), expected)

    def test_idempotent_and_preserves_optional_trailing_slash(self):
        for uri in (b"http://packages.linuxmint.com", b"http://packages.linuxmint.com/"):
            before = self.source.replace(b"http://packages.linuxmint.com", uri)
            after = repository_bytes(before)
            self.assertEqual(repository_bytes(after), after)
            self.assertEqual(after, before.replace(b"http://packages.linuxmint.com", b"https://fastly.linuxmint.io"))

    def test_rejects_unexpected_sources_without_returning_partial_changes(self):
        for data in (b"", self.source * 2, b"# " + self.source,
                     self.source.replace(b"zena", b"wilma"),
                     self.source.replace(b" main", b" romeo main"),
                     self.source.replace(b"deb ", b"deb [trusted=yes] "),
                     self.source.replace(b".com ", b".com.evil.invalid "),
                     self.source.replace(b"http:", b"https:"),
                     b"#" * 65537):
            with self.subTest(data=data[:100]), self.assertRaises(ValueError):
                repository_bytes(data)

    def test_command_refuses_non_ci_before_opening_host_files(self):
        env = dict(os.environ, GITHUB_ACTIONS="false")
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("mint_ci_repository.py"))],
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Disposable root CI container required", result.stderr)

    def test_both_native_fixtures_configure_before_normal_apt_authentication(self):
        for name in ("Test-LinuxSelfUpdateCI.sh", "Test-MintUatPairCI.sh"):
            text = Path(__file__).with_name(name).read_text()
            self.assertIn("python3 -I /work/tests/mint_ci_repository.py\napt-get update", text)
            self.assertNotIn("--allow-unauthenticated", text)


if __name__ == "__main__":
    unittest.main()
