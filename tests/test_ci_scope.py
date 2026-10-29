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
        for path in ("installer/src/App.tsx", "linux/lib/common.sh", "updater/Cargo.toml",
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
                    after["jobs"]["native"]["steps"].append({"run": "new build step"})
                elif change == "release":
                    after["jobs"]["release"]["if"] = "always"
                elif change == "trigger":
                    after["on"]["push"]["branches"].append("other")
                elif change == "gate":
                    after["jobs"]["checks"]["if"] = "false"
                else:
                    after["jobs"]["checks"]["needs"] = ["scope", "other"]
                self.assertTrue(application_required([WORKFLOW], before, after))


class RecoveryFeasibilityWorkflow(unittest.TestCase):
    def setUp(self):
        import yaml
        path = Path(__file__).resolve().parents[1] / WORKFLOW
        self.native = yaml.safe_load(path.read_text())["jobs"]["native"]
        self.steps = self.native["steps"]
        self.probes = [step for step in self.steps
                       if step.get("name") == "Required Windows acknowledgment feasibility"]

    def test_required_probe_is_on_windows_nsis_matrix(self):
        self.assertIn({"os": "windows-2022", "bundle": "nsis",
                       "asset": "Skyview-Dev-Setup-Windows-x64.exe"},
                      self.native["strategy"]["matrix"]["include"])
        self.assertEqual(len(self.probes), 1)
        self.assertEqual(self.probes[0]["if"],
                         "runner.os == 'Windows' && matrix.bundle == 'nsis'")
        self.assertEqual(self.probes[0]["shell"], "pwsh")
        self.assertNotIn("continue-on-error", self.probes[0])

    def test_probe_requires_exit_zero_and_both_exact_markers(self):
        self.assertEqual(len(self.probes), 1)
        script = self.probes[0]["run"]
        self.assertIn("-File ./tests/Test-RecoveryAcknowledgmentFeasibilityCI.ps1", script)
        self.assertIn("$probeExit = $LASTEXITCODE", script)
        self.assertIn('if ($probeExit -ne 0) { throw', script)
        self.assertIn("SDE_RECOVERY_WINDOWS_STANDARD_USER_INTENT_OK", script)
        self.assertIn("SDE_RECOVERY_WINDOWS_PRIVILEGED_CONSUMER_OK", script)
        self.assertIn('if ($output -cnotcontains $marker) { throw', script)
        self.assertIn("$output | Write-Output", script)

    def test_probe_is_separate_from_and_before_chocolatey_packaging(self):
        package = next(step for step in self.steps
                       if step.get("name") == "Package the existing Chocolatey backend")
        self.assertNotIn("Test-RecoveryAcknowledgmentFeasibilityCI.ps1", package["run"])
        self.assertLess(self.steps.index(self.probes[0]), self.steps.index(package))
        self.assertIn("Test-CoordinationCI.ps1", package["run"])


class RecoveryBootstrapWorkflow(unittest.TestCase):
    def setUp(self):
        import yaml
        root = Path(__file__).resolve().parents[1]
        self.root = root
        self.steps = yaml.safe_load((root / WORKFLOW).read_text())["jobs"]["native"]["steps"]

    def step(self, name):
        matching = [step for step in self.steps if step.get("name") == name]
        self.assertEqual(len(matching), 1)
        self.assertNotIn("continue-on-error", matching[0])
        return matching[0]

    def test_windows_installed_probe_is_required_after_install_and_before_upgrade(self):
        step = self.step("Required Windows installed recovery bootstrap")
        self.assertEqual(step["if"], "runner.os == 'Windows' && matrix.bundle == 'nsis'")
        self.assertEqual(step["shell"], "pwsh")
        self.assertIn("-File ./tests/Test-RecoveryBootstrapCI.ps1", step["run"])
        self.assertIn("$probeExit = $LASTEXITCODE", step["run"])
        self.assertIn("$probeExit -ne 0 -or $output -cnotcontains", step["run"])
        self.assertIn("SDE_RECOVERY_WINDOWS_INSTALLED_BOOTSTRAP_OK", step["run"])
        installed = self.step("Verify Windows application bootstrap without applying a baseline")
        upgrade = self.step("Build unpublished newer Windows fixture and verify signed SYSTEM upgrade")
        self.assertLess(self.steps.index(installed), self.steps.index(step))
        self.assertLess(self.steps.index(step), self.steps.index(upgrade))

    def test_linux_installed_probe_propagates_failure_and_requires_marker(self):
        step = self.step("Required Linux installed recovery bootstrap")
        self.assertEqual(step["if"], "runner.os == 'Linux'")
        self.assertEqual(step["shell"], "bash")
        self.assertIn("set -euo pipefail", step["run"])
        self.assertIn("sudo env GITHUB_ACTIONS=true python3 tests/verify_recovery_bootstrap_native.py", step["run"])
        self.assertIn("grep -Fxq SDE_RECOVERY_LINUX_INSTALLED_BOOTSTRAP_OK", step["run"])
        installed = self.step("Verify Linux application bootstrap without applying a baseline")
        self.assertLess(self.steps.index(installed), self.steps.index(step))

    def test_actual_mint_runs_installed_probe_before_applied_fixture(self):
        script = (self.root / "tests/Test-LinuxSelfUpdateCI.sh").read_text()
        invocation = 'python3 /work/tests/verify_recovery_bootstrap_native.py "$root/old.deb"'
        self.assertIn(invocation, script)
        self.assertIn("grep -Fxq SDE_RECOVERY_LINUX_INSTALLED_BOOTSTRAP_OK", script)
        self.assertLess(script.index(invocation), script.index("# Deterministic applied tool policy"))
        self.assertIn("set -Eeuo pipefail", script)


class CoordinationWorkflowExitContract(unittest.TestCase):
    def setUp(self):
        import yaml
        path = Path(__file__).resolve().parents[1] / WORKFLOW
        steps = yaml.safe_load(path.read_text())["jobs"]["update-trust"]["steps"]
        self.step = next(step for step in steps
                         if step.get("name") == "Native cross-process coordination contracts")

    def run_with_cargo_failure(self, failed_command, code):
        import subprocess
        # No real cargo/test/build invocation. Match Actions' explicit bash
        # fail-fast shell and simulate a failed native process in this step.
        stub = ('cargo() { printf "%s\\n" "$1"; '
                f'if [ "$1" = "{failed_command}" ]; then return {code}; fi; '
                'return 0; }\n')
        self.assertEqual(self.step["shell"], "bash")
        return subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o",
                               "pipefail", "-c", stub + self.step["run"]],
                              capture_output=True, text=True, check=False, timeout=10)

    def test_failed_tests_cannot_be_hidden_by_successful_formatting_or_clippy(self):
        result = self.run_with_cargo_failure("test", 23)
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["test"])

    def test_failed_formatting_stops_before_clippy(self):
        result = self.run_with_cargo_failure("fmt", 24)
        self.assertEqual(result.returncode, 24, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["test", "fmt"])


if __name__ == "__main__":
    unittest.main()
