"""Policy tests: fixture-only skipping must never swallow application changes."""
import copy
import unittest
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import ci_scope

from ci_scope import APPLICATION_JOBS, FIXTURE_PATHS, GATE, WORKFLOW, application_required


class CiScope(unittest.TestCase):
    def test_fixture_paths_skip_application_jobs(self):
        for path in FIXTURE_PATHS:
            with self.subTest(path=path):
                self.assertFalse(application_required([path]))

    def test_application_mixed_unknown_and_renamed_paths_require_builds(self):
        for path in ("installer/src/App.tsx", "installer/src/AppUpdateControl.tsx",
                     "installer/src-tauri/src/app_update.rs", "linux/lib/common.sh", "updater/Cargo.toml",
                     "tests/Prepare-MintNativeCI.sh", ".github/workflows/prepare-self-update-uat.yml",
                     "docs/RELEASE-NOTES-1.2.8.md", "unrecognized.txt", "old_fixture_name.py"):
            with self.subTest(path=path):
                self.assertTrue(application_required(["tests/native_uat_fixtures.py", path]))

    def test_empty_or_missing_workflow_content_fails_closed(self):
        self.assertTrue(application_required([]))
        self.assertTrue(application_required([WORKFLOW]))
        self.assertTrue(application_required([WORKFLOW], {}, {}))

    def test_non_pr_events_without_main_metadata_require_application_ci(self):
        for event in ("push", "workflow_dispatch", "unknown"):
            with self.subTest(event=event), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "output"
                with patch.dict(os.environ, {"CI_EVENT_NAME": event, "GITHUB_OUTPUT": str(output)}, clear=True), patch.object(ci_scope, "git") as git:
                    ci_scope.main()
                git.assert_not_called()
                self.assertEqual(output.read_text(), "application_required=true\n")

    def test_pr_checks_mergebase_without_filename_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with patch.dict(os.environ, {"CI_EVENT_NAME": "pull_request", "CI_BASE_SHA": "base", "CI_HEAD_SHA": "head", "GITHUB_OUTPUT": str(output)}), patch.object(ci_scope, "git", side_effect=[b"ancestor\n", b"tests/native_uat_fixtures.py\0"]) as git:
                ci_scope.main()
            self.assertEqual(output.read_text(), "application_required=false\n")
            self.assertEqual(git.call_args_list[1].args, ("diff", "--no-renames", "--name-only", "-z", "ancestor", "head"))

    def test_main_push_skips_only_exact_infrastructure_changes(self):
        import json
        import subprocess
        from ci_scope import MINT_INFRA_PATHS
        for paths, expected in [(sorted(MINT_INFRA_PATHS), False),
                                (['installer/src/App.tsx'], True),
                                (['tests/test_mint_host_inventory.py', 'updater/src/main.rs'], True),
                                (['tests/native_uat_fixtures.py'], True),
                                ([WORKFLOW], True), ([], True)]:
            with self.subTest(paths=paths), tempfile.TemporaryDirectory() as directory:
                event = Path(directory)/'event.json'; output = Path(directory)/'output'
                event.write_text(json.dumps({'ref': 'refs/heads/main', 'before': 'a'*40,
                                             'after': 'b'*40, 'deleted': False}))
                env = {'CI_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/main',
                       'GITHUB_SHA': 'b'*40, 'GITHUB_EVENT_PATH': str(event), 'GITHUB_OUTPUT': str(output)}
                raw = ('\0'.join(paths) + ('\0' if paths else '')).encode()
                with patch.dict(os.environ, env), patch.object(ci_scope, 'git', return_value=raw) as git:
                    ci_scope.main()
                git.assert_called_once_with('diff', '--no-renames', '--name-only', '-z', 'a'*40, 'b'*40)
                self.assertEqual(output.read_text(), f'application_required={str(expected).lower()}\n')

    def test_main_push_invalid_payload_refs_and_diff_fail_closed(self):
        import json
        import subprocess
        base = {'ref': 'refs/heads/main', 'before': 'a'*40, 'after': 'b'*40, 'deleted': False}
        for change in [{'before': '0'*40}, {'after': 'c'*40}, {'before': '--unsafe'},
                       {'deleted': True}, {'ref': 'refs/tags/v1.2.10'}]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                event = Path(directory)/'event.json'
                event.write_text(json.dumps(dict(base, **change)))
                with patch.dict(os.environ, {'GITHUB_REF': 'refs/heads/main', 'GITHUB_SHA': 'b'*40,
                                             'GITHUB_EVENT_PATH': str(event)}), patch.object(ci_scope, 'git') as git:
                    self.assertFalse(ci_scope.infrastructure_only_push())
                    git.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            event = Path(directory)/'event.json'; event.write_text(json.dumps(base))
            with patch.dict(os.environ, {'GITHUB_REF': 'refs/heads/main', 'GITHUB_SHA': 'b'*40,
                                         'GITHUB_EVENT_PATH': str(event)}), \
                 patch.object(ci_scope, 'git', side_effect=subprocess.CalledProcessError(1, 'git')):
                self.assertFalse(ci_scope.infrastructure_only_push())

    def workflows(self):
        before = {"on": {"pull_request": None, "push": {"branches": ["main"]}},
                  "jobs": {name: {"steps": [{"run": "preserve me"}]} for name in APPLICATION_JOBS}}
        before["jobs"]["release"] = {"if": "tag-only", "steps": [{"run": "publish"}]}
        after = copy.deepcopy(before)
        after["jobs"]["scope"] = {"steps": [{"run": "classify"}]}
        for name in APPLICATION_JOBS:
            after["jobs"][name].update(needs="scope", **{"if": GATE})
        return before, after

    def test_only_gate_introduction_is_allowed(self):
        before, after = self.workflows()
        self.assertFalse(application_required([WORKFLOW], before, after))
        self.assertFalse(application_required([WORKFLOW], after, after))

    def test_real_workflow_changes_require_application_ci(self):
        for change in ("steps", "release", "trigger", "gate", "needs"):
            with self.subTest(change=change):
                before, after = self.workflows()
                if change == "steps":
                    after["jobs"]["desktop-check"]["steps"].append({"run": "new build step"})
                elif change == "release":
                    after["jobs"]["release"]["if"] = "always"
                elif change == "trigger":
                    after["on"]["push"]["branches"].append("other")
                elif change == "gate":
                    after["jobs"]["checks"]["if"] = "false"
                else:
                    after["jobs"]["checks"]["needs"] = ["scope", "other"]
                self.assertTrue(application_required([WORKFLOW], before, after))


if __name__ == "__main__":
    unittest.main()
