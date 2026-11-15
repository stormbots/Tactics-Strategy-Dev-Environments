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




@unittest.skipUnless(os.name == "posix", "Linux Python probes require POSIX process groups")
class PythonRuntimeVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        import sys
        spec = importlib.util.spec_from_file_location("sde_python_runtime", ROOT / "linux/lib/python_runtime.py")
        cls.runtime = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.runtime
        spec.loader.exec_module(cls.runtime)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="python contract ")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.selected = self.make_executable(self.root / "Python 314")
        self.other = self.make_executable(self.root / "Python 315")
        self.calls = []
        self.fail_stage = None
        self.failure = self.runtime.Probe(7, "failed")
        self.project_base = self.selected
        self.project_is_venv = True
        self.pip = "pip 25.3 from test environment (python 3.14)"
        self.environment = None

    def make_executable(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
        return str(path)

    def run_probe(self, arguments, timeout):
        self.assertGreater(timeout, 0)
        self.assertLessEqual(timeout, 20)
        self.assertIn("-I", arguments)
        self.assertIn("-B", arguments)
        self.calls.append(arguments)
        stage = "identity"
        if "venv" in arguments:
            stage = "venv"
            self.environment = Path(arguments[-1])
        elif "pip" in arguments:
            stage = "pip"
        elif self.environment and arguments[0] == str(self.environment / "bin/python"):
            stage = "project"
        if stage == self.fail_stage:
            return self.failure
        if stage == "venv":
            self.make_executable(self.environment / "bin/python")
            return self.runtime.Probe(0)
        if stage == "pip":
            return self.runtime.Probe(0, self.pip)
        import json
        prefix = str(self.environment) if stage == "project" and self.project_is_venv else str(self.root)
        return self.runtime.Probe(0, json.dumps(dict(
            version="3.14.9", executable=arguments[0], prefix=prefix,
            basePrefix=str(self.root), baseExecutable=self.project_base if stage == "project" else self.selected)))

    def verify(self, find=None):
        return self.runtime.verify(run=self.run_probe, find=find or (lambda name: self.selected if name == "python3.14" else None))

    def test_one_explicit_python_owns_project_environment_and_pip(self):
        before = dict(os.environ)
        result = self.verify()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["version"], "3.14.9")
        self.assertEqual(result["executable"], self.selected)
        self.assertEqual(result["pipVersion"], "25.3")
        self.assertTrue(all(args[0] in (self.selected, str(self.environment / "bin/python")) for args in self.calls))
        self.assertFalse(self.environment.exists())
        self.assertEqual(dict(os.environ), before)

    def test_absence_and_unavailable_discovery_are_different(self):
        self.assertEqual(self.verify(find=lambda _: None)["status"], "notFound")
        def denied(_):
            raise PermissionError("test")
        self.assertEqual(self.verify(find=denied)["status"], "incomplete")
        self.assertEqual(self.calls, [])

    def test_version_text_with_failed_exit_never_passes(self):
        self.fail_stage = "identity"
        self.failure = self.runtime.Probe(1, 'Python 3.14.9')
        self.assertEqual(self.verify()["status"], "unusable")
        self.assertEqual(len(self.calls), 1)

    def test_each_failed_or_timed_out_requirement_keeps_readiness_unverified(self):
        for stage, reason in (("identity", "interpreter"), ("venv", "venv"), ("pip", "pip")):
            for timeout in (False, True):
                with self.subTest(stage=stage, timeout=timeout):
                    self.fail_stage = stage
                    self.failure = self.runtime.Probe(-1 if timeout else 7, reason="timeout" if timeout else "completed")
                    result = self.verify()
                    self.assertEqual(result["status"], "incomplete" if timeout else "unusable")
                    self.assertEqual(result["reason"], reason + ("Timeout" if timeout else "Failed"))
                    self.assertIsNone(result["pipVersion"])
                    if self.environment:
                        self.assertFalse(self.environment.exists())

    def test_pip_version_is_evidence_not_an_extra_release_constraint(self):
        self.pip = "pip 25.3.dev1+local.1 from test environment (python 3.14)"
        result = self.verify()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["pipVersion"], "25.3.dev1+local.1")

    def test_wrong_origin_or_non_environment_cannot_borrow_a_pip_pass(self):
        self.project_base = self.other
        self.assertEqual(self.verify()["reason"], "venvFailed")
        self.project_base = self.selected
        self.project_is_venv = False
        self.assertEqual(self.verify()["reason"], "venvFailed")
        self.project_is_venv = True
        self.pip = "pip 25.3 from another installation (python 3.15)"
        self.assertEqual(self.verify()["reason"], "pipFailed")

    @unittest.skipUnless(BASH, "Bash is required for the validator integration")
    def test_real_validator_fragment_counts_absent_python_and_helper_failure(self):
        source = (ROOT / "linux/Validate-SkyviewStudentDev.sh").read_text()
        fragment = source[source.index('PYTHON_RUNTIME='):source.index('\nif command -v git')]
        for missing_helper in (False, True):
            with self.subTest(missing_helper=missing_helper):
                directory = self.root if missing_helper else ROOT / "linux"
                program = 'PASS_COUNT=0; FAIL_COUNT=0\nfail() { printf "FAIL %s\\n" "$*"; FAIL_COUNT=$((FAIL_COUNT+1)); }\n' + fragment + '\nprintf "COUNTS %s %s\\n" "$PASS_COUNT" "$FAIL_COUNT"'
                result = subprocess.run([BASH, "--noprofile", "--norc", "-c", program], env={**os.environ, "PATH":"", "SCRIPT_DIR":str(directory), "SKYVIEW_LIB":str(self.root / "absent")}, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("COUNTS 0 1", result.stdout)
                if not missing_helper:
                    self.assertIn('"status":"notFound"', result.stdout)
                    self.assertEqual(result.stdout.count("SKYVIEW_EVENT|validation|FAIL|"), 1)

    def test_real_diagnostic_quoting_exit_and_timeout(self):
        import sys
        result = self.runtime.diagnostic([sys.executable, "-I", "-B", "-c", 'print("path with spaces and quotes: \\\"ok\\\"")'], 3)
        self.assertEqual(result.code, 0)
        self.assertIn('"ok"', result.text)
        self.assertEqual(self.runtime.diagnostic([sys.executable, "-I", "-B", "-c", "raise SystemExit(7)"], 3).code, 7)
        self.assertEqual(self.runtime.diagnostic([sys.executable, "-I", "-B", "-c", "import time; time.sleep(10)"], .1).reason, "timeout")

    def test_report_keeps_a_failed_requirement_distinct_from_a_crashed_helper(self):
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with redirect_stdout(output):
            code = self.runtime.report(self.verify(find=lambda _: None))
        self.assertEqual(code, 10)
        self.assertIn("SKYVIEW_EVENT|runtime|Python|", output.getvalue())
        self.assertIn("SKYVIEW_EVENT|validation|FAIL|Python:", output.getvalue())


@unittest.skipUnless(os.name == 'posix', 'Linux runtime inspection')
class LinuxNodePair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        import sys
        spec = importlib.util.spec_from_file_location('sde_node_runtime', ROOT / 'linux/lib/node_runtime.py')
        cls.runtime = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.runtime
        spec.loader.exec_module(cls.runtime)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='sde node contracts ')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.node = self.native('Node 24/bin/node')
        self.other = self.native('Node 26/bin/node')
        self.versions = {self.node: '24.19.0', self.other: '26.1.0'}
        self.calls = []
        self.fail_mode = None
        self.failure = self.runtime.Probe(7)
        self.npm_cli = str(self.root / 'Node 24/lib/node_modules/npm/bin/npm-cli.js')
        self.npm_version = '11.9.0'

    def native(self, name):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'\x7fELFfixture: never execute')
        path.chmod(0o700)
        return str(path)

    def run_probe(self, arguments, timeout):
        import json
        self.assertGreater(timeout, 0)
        self.assertLessEqual(timeout, 2.5)
        self.calls.append(arguments)
        mode = arguments[2] if arguments[1] == self.runtime.PROBE else 'cli'
        if mode == self.fail_mode:
            return self.failure
        if mode == 'cli':
            self.assertEqual(arguments[0], self.node)
            self.assertEqual(arguments[1], self.npm_cli)
            return self.runtime.Probe(0, self.npm_version)
        record = dict(version=self.versions[arguments[0]], executable=arguments[0])
        if mode == 'npm':
            record.update(npmVersion=self.npm_version, npmCli=self.npm_cli)
        return self.runtime.Probe(0, json.dumps(record))

    def verify(self, candidates=None, complete=True):
        return self.runtime.verify(run=self.run_probe, find=lambda: (candidates if candidates is not None else [self.node], complete))

    def test_pair_uses_selected_node_and_ignores_other_defaults(self):
        from unittest.mock import patch
        for version in ('22.1.0', '26.1.0'):
            self.versions[self.other] = version
            with patch.dict(os.environ, {'PATH': '/intentional/default', 'NVM_DIR': '/keep/selection'}):
                result = self.verify([self.other, self.node])
                self.assertEqual(os.environ['PATH'], '/intentional/default')
                self.assertEqual(os.environ['NVM_DIR'], '/keep/selection')
            self.assertEqual(result['status'], 'passed')
            self.assertEqual(result['executable'], self.node)
            self.assertEqual(result['npmVersion'], self.npm_version)
            self.assertEqual(result['maintenanceEligibility'], 'notEvaluated')
        self.assertTrue(all(call[0] == self.node for call in self.calls if call[1] != self.runtime.PROBE))

    def test_complete_pair_overrides_unrelated_discovery_failure(self):
        self.assertEqual(self.verify(complete=False)['status'], 'passed')

    def test_absent_is_different_from_incomplete(self):
        self.assertEqual(self.verify([])['status'], 'notFound')
        self.assertEqual(self.verify([self.other])['status'], 'notFound')
        self.assertEqual(self.verify([], False)['status'], 'incomplete')

    def test_broken_node_npm_and_timeout_cannot_pass(self):
        for mode in ('identity', 'npm', 'cli'):
            for failure in (self.runtime.Probe(7), self.runtime.Probe(-1, reason='timeout'),
                            self.runtime.Probe(0, '{bad'), self.runtime.Probe(-1, reason='invalidOutput')):
                with self.subTest(mode=mode, failure=failure):
                    self.fail_mode, self.failure = mode, failure
                    result = self.verify()
                    self.assertNotEqual(result['status'], 'passed')
                    self.assertIsNone(result['npmVersion'])
                    self.assertIsNone(result['npmCli'])

    def test_foreign_npm_never_executes(self):
        self.npm_cli = '/other-node/lib/node_modules/npm/bin/npm-cli.js'
        self.assertEqual(self.verify()['status'], 'unusable')
        self.assertFalse(any(call[1] != self.runtime.PROBE for call in self.calls))

    def test_cli_version_must_match_metadata(self):
        original = self.run_probe
        def run(arguments, timeout):
            return self.runtime.Probe(0, '99.0.0') if arguments[1] != self.runtime.PROBE else original(arguments, timeout)
        result = self.runtime.verify(run=run, find=lambda: ([self.node], True))
        self.assertEqual(result['reason'], 'npmFailed')
        self.assertEqual(result['status'], 'unusable')

    def test_next_complete_pair_can_succeed_after_broken_candidate(self):
        first = self.native('broken/bin/node')
        self.versions[first] = '24.18.0'
        original = self.run_probe
        def run(arguments, timeout):
            return self.runtime.Probe(7) if arguments[0] == first else original(arguments, timeout)
        result = self.runtime.verify(run=run, find=lambda: ([first, self.node], True))
        self.assertEqual(result['status'], 'passed')

    def test_reverify_actual_executable_after_symlink(self):
        alias = self.root / 'selected-node'
        alias.symlink_to(self.node)
        original = self.run_probe
        def run(arguments, timeout):
            if arguments[0] == str(alias):
                import json
                return self.runtime.Probe(0, json.dumps(dict(version='24.19.0', executable=self.node)))
            return original(arguments, timeout)
        result = self.runtime.verify(run=run, find=lambda: ([str(alias)], True))
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['executable'], self.node)

    def test_discover_cached_stores_without_executing_managers(self):
        from unittest.mock import patch
        paths = [self.native('.nvm/versions/node/v24.19.0/bin/node'),
                 self.native('.volta/tools/image/node/24.19.0/bin/node'),
                 self.native('.local/share/fnm/node-versions/v24.19.0/installation/bin/node')]
        with patch.object(Path, 'home', return_value=self.root), patch.dict(os.environ, {'NVM_DIR': '', 'VOLTA_HOME': '', 'FNM_DIR': '', 'XDG_DATA_HOME': ''}), patch.object(self.runtime.shutil, 'which', return_value=None):
            candidates, complete = self.runtime.discover()
        self.assertTrue(all(path in candidates for path in paths))
        self.assertTrue(complete)

    def test_store_truncation_and_shell_shims_are_incomplete(self):
        from unittest.mock import patch
        for index in range(9):
            self.native(f'.nvm/versions/node/v24.0.{index}/bin/node')
        shim = self.root / 'shell-node'
        shim.write_text('#!/bin/sh\nexit 99\n')
        shim.chmod(0o700)
        with patch.object(Path, 'home', return_value=self.root), patch.dict(os.environ, {'NVM_DIR': '', 'VOLTA_HOME': '', 'FNM_DIR': '', 'XDG_DATA_HOME': ''}), patch.object(self.runtime.shutil, 'which', return_value=str(shim)):
            candidates, complete = self.runtime.discover()
        self.assertFalse(complete)
        self.assertNotIn(str(shim), candidates)
        self.assertLessEqual(len(candidates), 12)

    def test_volta_launcher_and_unreadable_discovery_are_incomplete(self):
        from unittest.mock import patch
        launcher = self.native('.volta/bin/node')
        with patch.object(Path, 'home', return_value=self.root), patch.dict(os.environ, {'VOLTA_HOME': ''}), patch.object(self.runtime.shutil, 'which', return_value=launcher):
            candidates, complete = self.runtime.discover()
        self.assertFalse(complete)
        self.assertNotIn(launcher, candidates)
        with patch.object(self.runtime.os, 'scandir', side_effect=PermissionError('denied')), patch.object(self.runtime.shutil, 'which', return_value=None):
            _, complete = self.runtime.discover()
        self.assertFalse(complete)

    def test_actual_process_adapter_is_bounded_and_preserves_environment(self):
        import sys
        from unittest.mock import patch
        with patch.dict(os.environ, {'NODE_OPTIONS': '--invalid-flag', 'npm_config_registry': 'https://invalid.example'}):
            result = self.runtime.diagnostic([sys.executable, '-I', '-c', 'import os; print(os.getcwd()); print(os.getenv("NODE_OPTIONS")); print(os.getenv("npm_config_registry")); print("café path with spaces")'], 2)
            self.assertEqual(os.environ['NODE_OPTIONS'], '--invalid-flag')
        self.assertEqual(result.code, 0)
        self.assertIn('None\nNone\ncafé path with spaces', result.text)
        self.assertFalse(Path(result.text.splitlines()[0]).exists())
        self.assertEqual(self.runtime.diagnostic([sys.executable, '-I', '-c', 'raise SystemExit(7)'], 2).code, 7)
        self.assertEqual(self.runtime.diagnostic([sys.executable, '-I', '-c', 'import time; time.sleep(10)'], .1).reason, 'timeout')
        for pipe in ('stdout', 'stderr'):
            self.assertEqual(self.runtime.diagnostic([sys.executable, '-I', '-c', f'import sys; sys.{pipe}.write("x" * 100000)'], 2).reason, 'invalidOutput')

    def test_actual_prepared_node_and_npm_and_compatibility_probe(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Prepared Node 24 is required by this CI contract')
        result = self.runtime.verify(find=lambda: ([str(Path(node).resolve())], True))
        self.assertEqual(result['status'], 'passed', result)
        self.assertEqual(result['executable'], str(Path(node).resolve()))
        fixture = subprocess.run([node, str(ROOT / 'tests/test_node_runtime_probe.cjs'), '--linux'], capture_output=True, text=True, timeout=10)
        self.assertEqual(fixture.returncode, 0, fixture.stdout + fixture.stderr)
        self.assertIn('LINUX_NODE_RUNTIME_PROBE_CONTRACTS_OK', fixture.stdout)

    def test_report_counts_only_one_required_pair(self):
        import contextlib
        import io
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = self.runtime.report(self.verify())
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue().count('SKYVIEW_EVENT|validation|PASS|Node.js:'), 1)
        self.assertIn('SKYVIEW_EVENT|runtime|Node.js|', output.getvalue())

    def test_real_validator_fragment_counts_pair_and_helper_failure(self):
        source = (ROOT / 'linux/Validate-SkyviewStudentDev.sh').read_text()
        fragment = source[source.index('NODE_RUNTIME='):source.index('# One explicit interpreter')]
        for missing in (False, True):
            program = 'PASS_COUNT=0; FAIL_COUNT=0\nfail() { printf "FAIL %s\\n" "$*"; FAIL_COUNT=$((FAIL_COUNT+1)); }\n' + fragment + '\nprintf "COUNTS %s %s\\n" "$PASS_COUNT" "$FAIL_COUNT"'
            result = subprocess.run([BASH, '--noprofile', '--norc', '-c', program],
                                    env={**os.environ, 'SCRIPT_DIR': str(self.root if missing else ROOT / 'linux'), 'SKYVIEW_LIB': str(self.root / 'absent')},
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('COUNTS 0 1' if missing else 'COUNTS 1 0', result.stdout)
            if not missing:
                self.assertEqual(result.stdout.count('SKYVIEW_EVENT|runtime|Node.js|'), 1)
                self.assertEqual(result.stdout.count('SKYVIEW_EVENT|validation|PASS|Node.js:'), 1)

    def test_node_observation_supplies_metadata_without_bare_npm(self):
        import json
        record = self.verify()
        result = subprocess.run(['/usr/bin/python3', str(ROOT / 'linux/lib/tool_records.py'), '--node-observation'],
                                input=json.dumps(record), text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        events = [line.split('|', 3) for line in result.stdout.splitlines() if line.startswith('SKYVIEW_EVENT|tool|')]
        rows = {event[2]: json.loads(event[3]) for event in events}
        self.assertEqual(rows['Node.js']['installedVersion'], '24.19.0')
        self.assertEqual(rows['npm']['installedVersion'], '11.9.0')


if __name__ == "__main__":
    unittest.main()
