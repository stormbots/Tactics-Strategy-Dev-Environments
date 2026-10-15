"""Exercise real filesystem/Git round trips only in temporary fixture roots."""
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_uat_fixtures as fixtures


class NativeFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.root = self.base / "state"
        self.workspace = self.home / "Development"
        self.workspace.mkdir()
        self.git = self.home / ".gitconfig"
        self.git.write_bytes(b'[init]\n\tdefaultBranch = main\n# retained comment\n')
        self.repo = self.home / "repositories.csv"
        self.repo.write_bytes(b'name,url,branch,enabled\n')
        self.who = {"system": "mint", "host": "disposable", "user": "uat", "home": str(self.home)}
        self.paths = {"workspace": self.workspace, "git-manual": self.git, "mentor-repository": self.repo}
        for mock in (patch.object(fixtures, "identity", return_value=self.who),
                     patch.object(fixtures, "targets", return_value=self.paths),
                     patch.dict(os.environ, {**{key: value for key, value in os.environ.items() if not key.startswith("GIT_CONFIG")}, "HOME": str(self.home), "USERPROFILE": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config")}, clear=True),
                     contextlib.redirect_stdout(io.StringIO())):
            mock.__enter__()
            self.addCleanup(mock.__exit__, None, None, None)
        fixtures.enroll(self.root, True)

    def test_workspace_roundtrip_and_idempotent_restore(self):
        fixtures.apply(self.root, "workspace")
        self.assertFalse(self.workspace.exists())
        fixtures.restore(self.root)
        fixtures.restore(self.root)
        self.assertTrue(self.workspace.is_dir())
        self.assertIsNone(fixtures.load(self.root)["active"])

    def test_never_moves_student_work(self):
        (self.workspace / "project.txt").write_text("keep")
        with self.assertRaises(ValueError):
            fixtures.apply(self.root, "workspace")
        self.assertEqual((self.workspace / "project.txt").read_text(), "keep")

    def test_repair_recreated_workspace_requires_snapshot(self):
        fixtures.apply(self.root, "workspace")
        self.workspace.mkdir()
        with self.assertRaises(ValueError):
            fixtures.restore(self.root)
        self.assertIsNotNone(fixtures.load(self.root)["active"])

    def test_git_roundtrip_preserves_exact_bytes(self):
        before = self.git.read_bytes()
        fixtures.apply(self.root, "git-manual")
        self.assertEqual(fixtures.run("git", "config", "--global", "--get", "init.defaultBranch"), "uat-fixture")
        fixtures.restore(self.root)
        self.assertEqual(self.git.read_bytes(), before)

    def test_drift_is_preserved(self):
        fixtures.apply(self.root, "git-manual")
        self.git.write_text("# edited during UAT\n")
        with self.assertRaises(ValueError):
            fixtures.restore(self.root)
        self.assertEqual(self.git.read_text(), "# edited during UAT\n")

    def test_second_fixture_rejected(self):
        fixtures.apply(self.root, "workspace")
        with self.assertRaises(ValueError):
            fixtures.apply(self.root, "git-manual")

    def test_mentor_roundtrip_both_native_schemas(self):
        for system, header in (("mint", b'name,url,branch,enabled\n'), ("windows", b'Name,Url,Folder\r\n')):
            self.who["system"] = system
            state = fixtures.load(self.root) if system == "mint" else json.loads((self.root / "state.json").read_text())
            state["identity"] = self.who
            fixtures.save(self.root, state)
            self.repo.write_bytes(header)
            fixtures.apply(self.root, "mentor-repository")
            self.assertIn("https://example.invalid/uat-only.git", self.repo.read_text())
            fixtures.restore(self.root)
            self.assertEqual(self.repo.read_bytes(), header)

    def test_real_repository_config_rejected(self):
        self.repo.write_text("name,url,branch,enabled\nstudent,https://example.com/project,main,true\n")
        with self.assertRaises(ValueError):
            fixtures.apply(self.root, "mentor-repository")

    def test_wrong_host_and_missing_acknowledgement(self):
        with patch.object(fixtures, "identity", return_value={**self.who, "host": "other"}):
            with self.assertRaises(ValueError):
                fixtures.restore(self.root)
        with self.assertRaises(ValueError):
            fixtures.enroll(self.base / "other", False)

    def test_interruption_before_mutation_can_restore(self):
        with patch.object(Path, "rename", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                fixtures.apply(self.root, "workspace")
        self.assertIsNotNone(fixtures.load(self.root)["active"])
        fixtures.restore(self.root)
        self.assertTrue(self.workspace.is_dir())

    @unittest.skipIf(os.name == "nt", "POSIX link fixture")
    def test_symlink_target_rejected(self):
        original = self.home / "original"
        self.git.rename(original)
        self.git.symlink_to(original)
        with self.assertRaises(ValueError):
            fixtures.apply(self.root, "git-manual")
        self.assertIn(b"defaultBranch = main", original.read_bytes())


    def test_state_directory_cannot_move_with_workspace(self):
        with self.assertRaises(ValueError):
            fixtures.enroll(self.workspace / "fixture-state", True)
        self.assertFalse((self.workspace / "fixture-state").exists())

    def test_pending_file_intent_without_mutation_restores(self):
        before = self.git.read_bytes()
        original_write = Path.write_bytes
        def interrupt(path, data):
            if path == self.git:
                raise OSError("interrupted")
            return original_write(path, data)
        with patch.object(Path, "write_bytes", interrupt):
            with self.assertRaises(OSError):
                fixtures.apply(self.root, "git-manual")
        fixtures.restore(self.root)
        self.assertEqual(self.git.read_bytes(), before)

    def test_deleted_configuration_is_not_recreated(self):
        fixtures.apply(self.root, "git-manual")
        self.git.unlink()
        with self.assertRaises(ValueError):
            fixtures.restore(self.root)
        self.assertFalse(self.git.exists())

    def test_windows_acl_path_is_data_not_powershell_code(self):
        with patch.object(fixtures.os, "name", "nt"), patch.object(fixtures.subprocess, "run") as invoke:
            invoke.return_value.returncode = 0
            fixtures.secure(self.root)
        args, kwargs = invoke.call_args
        self.assertEqual(args[0][-2], "-EncodedCommand")
        script = base64.b64decode(args[0][-1]).decode("utf-16-le")
        self.assertIn("$env:SDE_UAT_STATE_PATH", script)
        self.assertNotIn(str(self.root), script)
        self.assertEqual(kwargs["env"]["SDE_UAT_STATE_PATH"], str(self.root))

    def test_permission_denied_keeps_recoverable_intent(self):
        with patch.object(Path, "rename", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                fixtures.apply(self.root, "workspace")
        self.assertIsNotNone(fixtures.load(self.root)["active"])
        fixtures.restore(self.root)
        self.assertTrue(self.workspace.is_dir())

    def test_existing_lock_rejected(self):
        (self.root / "operation.lock").touch()
        class Args:
            action = "restore"
        with self.assertRaises(FileExistsError):
            fixtures.execute(Args(), self.root)


if __name__ == "__main__":
    unittest.main()
