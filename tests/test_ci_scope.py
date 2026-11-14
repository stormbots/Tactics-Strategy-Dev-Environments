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
                     "docs/runtime-config.json", "unrecognized.txt", "old_fixture_name.py"):
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
                self.assertEqual(output.read_text(), "application_required=true\nnative_required=true\ndocumentation_required=false\ndocumentation_paths=[]\n")

    def test_pr_checks_mergebase_without_filename_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with patch.dict(os.environ, {"CI_EVENT_NAME": "pull_request", "CI_BASE_SHA": "base", "CI_HEAD_SHA": "head", "GITHUB_OUTPUT": str(output)}), patch.object(ci_scope, "git", side_effect=[b"ancestor\n", b"tests/native_uat_fixtures.py\0"]) as git:
                ci_scope.main()
            self.assertEqual(output.read_text(), "application_required=false\nnative_required=false\ndocumentation_required=false\ndocumentation_paths=[]\n")
            self.assertEqual(git.call_args_list[1].args, ("diff", "--no-renames", "--name-only", "-z", "ancestor", "head"))

    def test_main_push_skips_only_exact_infrastructure_changes(self):
        import json
        import subprocess
        from ci_scope import MINT_INFRA_PATHS
        for paths, expected in [(sorted(MINT_INFRA_PATHS - ci_scope.POLICY_PATHS), False),
                                (sorted(ci_scope.POLICY_PATHS), True),
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
                with patch.dict(os.environ, env), patch.object(ci_scope, 'git', side_effect=lambda *args: raw if args[0] == 'diff' else b'100644 blob abc\tdocs/MINT-HOST-INVENTORY.md\0') as git:
                    ci_scope.main()
                self.assertEqual(git.call_args_list[0].args, ('diff', '--no-renames', '--name-only', '-z', 'a'*40, 'b'*40))
                self.assertEqual(git.call_count, 3 if any(map(ci_scope.documentation_path, paths)) else 1)
                self.assertEqual(output.read_text(), f'application_required={str(expected).lower()}\nnative_required={str(expected).lower()}\ndocumentation_required={str(any(ci_scope.documentation_path(p) for p in paths)).lower()}\ndocumentation_paths=' + __import__('json').dumps([p for p in paths if ci_scope.documentation_path(p)]) + '\n')

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

    def test_even_gate_only_workflow_changes_validate_full_pipeline(self):
        before, after = self.workflows()
        self.assertTrue(application_required([WORKFLOW], before, after))
        self.assertTrue(application_required([WORKFLOW], after, after))

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


class PresentationScope(unittest.TestCase):
    def test_every_explicit_presentation_path_is_pr_only(self):
        for path in ci_scope.PRESENTATION_PATHS:
            with self.subTest(path=path):
                self.assertFalse(ci_scope.native_required([path], 'pull_request'))
                for event in ('push', 'workflow_dispatch', 'merge_group', 'unknown', None):
                    self.assertTrue(ci_scope.native_required([path], event))

    def test_unknown_mixed_native_dependencies_and_policy_changes_fail_closed(self):
        for path in ('installer/src/bridge.ts', 'installer/src/recovery.ts',
                     'installer/src/updateDiscovery.ts', 'installer/src/safeOperations.ts',
                     'installer/src/newUnknown.ts', 'installer/src-tauri/src/main.rs',
                     'installer/package-lock.json', 'installer/package.json',
                     'installer/playwright.config.ts', 'tests/ci_scope.py',
                     'tests/test_ci_scope.py', WORKFLOW, 'updater/src/main.rs',
                     'coordination/src/safety.rs', 'linux/lib/schedule.py',
                     'windows/Install-SkyviewStudentDev.ps1', '../installer/src/App.tsx'):
            with self.subTest(path=path):
                self.assertTrue(ci_scope.native_required(['installer/src/style.css', path], 'pull_request'))
        self.assertTrue(ci_scope.native_required([], 'pull_request'))
        for path in ci_scope.POLICY_PATHS:
            self.assertTrue(application_required([path]))

    def test_removed_and_renamed_unknown_paths_require_native_checks(self):
        self.assertTrue(ci_scope.native_required(['old-name.ts', 'installer/src/App.tsx'], 'pull_request'))

    def test_real_presentation_pr_emits_checks_true_native_false(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            with patch.dict(os.environ, {'CI_EVENT_NAME': 'pull_request', 'CI_BASE_SHA': 'base',
                                         'CI_HEAD_SHA': 'head', 'GITHUB_OUTPUT': str(output)}), \
                 patch.object(ci_scope, 'git', side_effect=[b'ancestor\n', b'installer/src/style.css\0']):
                ci_scope.main()
            self.assertEqual(output.read_text(), 'application_required=true\nnative_required=false\ndocumentation_required=false\ndocumentation_paths=[]\n')

    def test_native_and_trust_wait_for_checks_without_changing_native_steps(self):
        import yaml
        root = Path(__file__).resolve().parents[1]
        jobs = yaml.safe_load((root / WORKFLOW).read_text())['jobs']
        for name in ('native', 'update-trust'):
            self.assertEqual(jobs[name]['needs'], ['scope', 'checks'])
            self.assertEqual(jobs[name]['if'], "needs.scope.outputs.native_required == 'true'")
        self.assertEqual(jobs['checks']['if'], ci_scope.GATE)
        self.assertEqual(jobs['acceptance']['if'], 'always()')
        self.assertEqual(jobs['acceptance']['needs'], ['scope', 'checks', 'native', 'update-trust'])

    def test_acceptance_fails_for_required_missing_failed_cancelled_jobs_or_scope(self):
        import subprocess
        import yaml
        root = Path(__file__).resolve().parents[1]
        script = yaml.safe_load((root / WORKFLOW).read_text())['jobs']['acceptance']['steps'][0]['run']
        full = dict(SCOPE_RESULT='success', CHECKS_RESULT='success', NATIVE_RESULT='success',
                    TRUST_RESULT='success', APPLICATION_REQUIRED='true', NATIVE_REQUIRED='true', DOCUMENTATION_REQUIRED='false')
        presentation = dict(full, NATIVE_REQUIRED='false', NATIVE_RESULT='skipped', TRUST_RESULT='skipped')
        fixture = dict(presentation, APPLICATION_REQUIRED='false', CHECKS_RESULT='skipped')
        for env in (full, presentation, fixture):
            self.assertEqual(subprocess.run(['bash', '-e', '-c', script], env=dict(os.environ, **env), capture_output=True).returncode, 0)
        for key in ('SCOPE_RESULT', 'CHECKS_RESULT', 'NATIVE_RESULT', 'TRUST_RESULT'):
            for value in ('failure', 'cancelled', 'skipped', ''):
                env = dict(full, **{key: value})
                with self.subTest(key=key, value=value):
                    self.assertNotEqual(subprocess.run(['bash', '-e', '-c', script], env=dict(os.environ, **env), capture_output=True).returncode, 0)
        for key in ('APPLICATION_REQUIRED', 'NATIVE_REQUIRED', 'DOCUMENTATION_REQUIRED'):
            env = dict(full, **{key: ''})
            self.assertNotEqual(subprocess.run(['bash', '-e', '-c', script], env=dict(os.environ, **env), capture_output=True).returncode, 0)


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

    def test_linux_manual_supervisor_is_required_on_host_and_actual_mint(self):
        step = self.step("Required Linux installed manual recovery supervisor")
        self.assertEqual(step["if"], "runner.os == 'Linux'")
        self.assertEqual(step["shell"], "bash")
        self.assertIn("set -euo pipefail", step["run"])
        self.assertIn("sudo env GITHUB_ACTIONS=true python3 tests/verify_manual_recovery_native.py", step["run"])
        marker = "grep -Fxq SDE_RECOVERY_LINUX_MANUAL_SUPERVISOR_OK"
        self.assertIn(marker, step["run"])
        bootstrap = self.step("Required Linux installed recovery bootstrap")
        upgrade = self.step("Required signed upgrade on Linux Mint 22.3")
        self.assertLess(self.steps.index(bootstrap), self.steps.index(step))
        self.assertLess(self.steps.index(step), self.steps.index(upgrade))
        script = (self.root / "tests/Test-LinuxSelfUpdateCI.sh").read_text()
        invocation = "python3 /work/tests/verify_manual_recovery_native.py"
        self.assertIn(invocation, script)
        self.assertIn(marker, script)
        self.assertLess(script.index(invocation), script.index("# Deterministic applied tool policy"))

    def test_windows_manual_maintenance_requires_installed_release_and_marker(self):
        step = self.step("Required Windows installed manual maintenance recovery")
        self.assertEqual(step["if"], "runner.os == 'Windows' && matrix.bundle == 'nsis'")
        self.assertEqual(step["shell"], "pwsh")
        self.assertIn("-File ./tests/Test-WindowsManualRecoveryCI.ps1", step["run"])
        self.assertIn("$probeExit = $LASTEXITCODE", step["run"])
        self.assertIn("$probeExit -ne 0 -or $output -cnotcontains 'SDE_RECOVERY_WINDOWS_MANUAL_MAINTENANCE_OK'", step["run"])
        self.assertIn("$output -cnotcontains 'SDE_RECOVERY_WINDOWS_MANUAL_INSTALL_REPAIR_OK'", step["run"])
        installed = self.step("Required Windows installed recovery bootstrap")
        upgrade = self.step("Build unpublished newer Windows fixture and verify signed SYSTEM upgrade")
        self.assertLess(self.steps.index(installed), self.steps.index(step))
        self.assertLess(self.steps.index(step), self.steps.index(upgrade))

    def test_windows_package_hook_gate_keeps_exit_and_both_required_markers(self):
        step = self.step("Package the existing Chocolatey backend")
        self.assertIn("$coordinationExit = $LASTEXITCODE", step["run"])
        self.assertIn("$coordinationExit -ne 0", step["run"])
        for marker in ('WINDOWS_COORDINATION_SUPERVISION_OK', 'SDE_WINDOWS_PACKAGE_HOOK_PARENT_REQUIRED_OK', 'SDE_RECOVERY_WINDOWS_READONLY_VALIDATION_OK'):
            self.assertIn("$coordinationOutput -cnotcontains '" + marker + "'", step["run"])
        self.assertLess(step["run"].index('$coordinationExit = $LASTEXITCODE'),
                        step["run"].index('$coordinationOutput | Write-Output'))


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



class DocumentationScope(unittest.TestCase):
    def test_reference_formats_are_light_on_prs_and_main(self):
        for path in ('README.md', 'docs/new-guide.md', 'docs/student-development-manual/new.md',
                     'docs/figures/diagram.svg', 'docs/figures/screen.png', 'docs/RELEASE-NOTES-1.2.23.md'):
            for event, ref in (('pull_request', ''), ('push', 'refs/heads/main')):
                with self.subTest(path=path, event=event):
                    self.assertEqual(ci_scope.classify([path], event, ref), (False, False, True))

    def test_mixed_unknown_consumed_config_policy_and_execution_paths_stay_full(self):
        for path in ('docs/helper.py', 'docs/mockup-new.html', 'docs/schema.json', 'docs/AGENTS.md',
                     'docs/../installer/src/App.tsx', '/docs/guide.md', 'docs//guide.md',
                     'installer/src/App.tsx', 'installer/src/model.ts', 'installer/src/PreflightReview.tsx',
                     'installer/src/overviewDecision.ts', 'installer/src/recovery.ts',
                     'tests/ci_scope.py', 'tests/test_ci_scope.py', 'tests/check_docs.py',
                     'tests/test_check_docs.py', WORKFLOW, 'installer/package-lock.json',
                     'linux/Validate-SkyviewStudentDev.sh', 'unknown.bin'):
            with self.subTest(path=path):
                self.assertEqual(ci_scope.classify(['docs/guide.md', path], 'pull_request'), (True, True, True))
        self.assertEqual(ci_scope.classify(['docs/guide.md'], 'pull_request', unsafe_documents=['docs/guide.md']), (True, True, True))

    def test_registered_automation_inputs_are_full_even_with_markdown_suffixes(self):
        with patch.object(ci_scope, 'FULL_REFERENCE_PATHS', {'docs/runtime-settings.md'}):
            self.assertEqual(ci_scope.classify(['docs/runtime-settings.md'], 'pull_request'), (True, True, False))

    def test_releases_manual_unknown_events_and_empty_ranges_stay_full(self):
        for event, ref in (('workflow_dispatch', ''), ('unknown', ''), ('merge_group', ''),
                           ('push', 'refs/tags/v1.2.24'), ('push', 'refs/heads/release/v1.2.24')):
            self.assertEqual(ci_scope.classify(['docs/guide.md'], event, ref), (True, True, True))
        for paths in (None, [], ['']):
            self.assertEqual(ci_scope.classify(paths, 'pull_request'), (True, True, False))

    def test_docs_can_accompany_presentation_but_not_hide_application_main_changes(self):
        paths = ['docs/guide.md', 'installer/src/style.css']
        self.assertEqual(ci_scope.classify(paths, 'pull_request'), (True, False, True))
        self.assertEqual(ci_scope.classify(paths, 'push', 'refs/heads/main'), (True, True, True))

    def test_actual_pr_and_main_emit_a_data_manifest_and_check_both_file_modes(self):
        import json
        for event in ('pull_request', 'push'):
            with self.subTest(event=event), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'output'; payload = Path(directory) / 'event.json'
                payload.write_text(json.dumps(dict(ref='refs/heads/main', before='a'*40, after='b'*40, deleted=False)))
                env = dict(CI_EVENT_NAME=event, GITHUB_REF='refs/heads/main', GITHUB_SHA='b'*40,
                           CI_BASE_SHA='a'*40, CI_HEAD_SHA='b'*40, GITHUB_EVENT_PATH=str(payload), GITHUB_OUTPUT=str(output))
                modes = b'100644 blob fff\tdocs/guide.md\0'
                reads = ([b'a'*40+b'\n'] if event == 'pull_request' else []) + [b'docs/guide.md\0', modes, modes]
                with patch.dict(os.environ, env), patch.object(ci_scope, 'git', side_effect=reads) as git:
                    ci_scope.main()
                values = dict(line.split('=', 1) for line in output.read_text().splitlines())
                self.assertEqual(values, dict(application_required='false', native_required='false', documentation_required='true', documentation_paths='["docs/guide.md"]'))
                self.assertEqual(git.call_args_list[-2].args, ('ls-tree','-r','-z','a'*40,'--','README.md','docs'))
                self.assertEqual(git.call_args_list[-1].args, ('ls-tree','-r','-z','b'*40,'--','README.md','docs'))

    def test_real_git_pr_ranges_keep_doc_renames_light_but_executable_modes_full(self):
        import json
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def command(*args):
                return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL)
            def commit(message):
                command('add', '--all')
                command('-c', 'user.name=CI fixture', '-c', 'user.email=ci@example.invalid', 'commit', '-qm', message)
                return command('rev-parse', 'HEAD').decode().strip()
            command('init', '-q')
            (root / 'README.md').write_text('# Initial\n')
            base = commit('Initial')
            (root / 'README.md').write_text('# Updated\n')
            first = commit('Edit reference')
            (root / 'docs').mkdir()
            command('mv', 'README.md', 'docs/guide.md')
            renamed = commit('Rename reference')
            command('update-index', '--chmod=+x', 'docs/guide.md')
            command('-c', 'user.name=CI fixture', '-c', 'user.email=ci@example.invalid', 'commit', '-qm', 'Executable mode')
            executable = command('rev-parse', 'HEAD').decode().strip()
            for older, head, full in ((base, first, False), (first, renamed, False), (renamed, executable, True)):
                output = root / 'output'
                output.write_text('')
                with patch.dict(os.environ, dict(CI_EVENT_NAME='pull_request', CI_BASE_SHA=older, CI_HEAD_SHA=head, GITHUB_OUTPUT=str(output))), patch.object(ci_scope, 'git', side_effect=command):
                    ci_scope.main()
                values = dict(line.split('=',1) for line in output.read_text().splitlines())
                self.assertEqual(values['application_required'], str(full).lower())
                self.assertEqual(values['native_required'], str(full).lower())
                self.assertEqual(values['documentation_required'], 'true')
                self.assertEqual(set(json.loads(values['documentation_paths'])), {'docs/guide.md', 'README.md'} if head == renamed else {'docs/guide.md'} if full else {'README.md'})

    def test_symlink_or_executable_prose_cannot_earn_a_shortcut(self):
        for mode in ('120000', '100755'):
            with patch.object(ci_scope, 'git', side_effect=[f'{mode} blob abc\tdocs/guide.md\0'.encode(), b'']):
                self.assertEqual(ci_scope.unsafe_documentation_paths(['docs/guide.md'], 'base', 'head'), {'docs/guide.md'})

    def test_only_reference_steps_run_on_docs_and_acceptance_enforces_their_result(self):
        import subprocess
        import yaml
        root = Path(__file__).resolve().parents[1]
        jobs = yaml.safe_load((root / WORKFLOW).read_text())['jobs']
        steps = jobs['checks']['steps']
        for step in steps:
            if (step.get('working-directory') == 'installer' or step.get('uses', '').startswith(('actions/setup-node@', 'docker://', 'actions/upload-artifact@'))
                    or step.get('name') == 'Bash static analysis and integrity'):
                self.assertEqual(step['if'], "needs.scope.outputs.application_required == 'true'")
        docs = next(s for s in steps if s.get('name') == 'Validate changed reference documents')
        self.assertEqual(docs['env']['DOCUMENTATION_PATHS'], '${{ needs.scope.outputs.documentation_paths }}')
        self.assertEqual(docs['run'], 'python3 tests/check_docs.py\npython3 -m unittest discover -s tests -p test_uat_version.py\n')
        script = jobs['acceptance']['steps'][0]['run']
        env = dict(os.environ, SCOPE_RESULT='success', CHECKS_RESULT='success', NATIVE_RESULT='skipped',
                   TRUST_RESULT='skipped', APPLICATION_REQUIRED='false', NATIVE_REQUIRED='false', DOCUMENTATION_REQUIRED='true')
        self.assertEqual(subprocess.run(['bash','-e','-c',script], env=env, capture_output=True).returncode, 0)
        for result in ('failure', 'cancelled', 'skipped', ''):
            env['CHECKS_RESULT'] = result
            self.assertNotEqual(subprocess.run(['bash','-e','-c',script], env=env, capture_output=True).returncode, 0)
        env.update(CHECKS_RESULT='success', DOCUMENTATION_REQUIRED='')
        self.assertNotEqual(subprocess.run(['bash','-e','-c',script], env=env, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
