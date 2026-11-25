"""Metadata fixtures: never provision the host."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "linux/lib" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value
tools = module("tool_records")
schedule = module("schedule")
git_preferences = module('git_preferences')


class GitPreferences(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sde git préférences ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'student.gitconfig'
        self.system = self.root / 'system.gitconfig'
        self.system.write_text('')
        self.git = shutil.which('git')
        self.assertIsNotNone(self.git, 'Prepared native Git required')
        environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        environment.update(GIT_CONFIG_GLOBAL=str(self.config), GIT_CONFIG_SYSTEM=str(self.system))
        self.environment = patch.dict(os.environ, environment, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def check(self):
        return git_preferences.verify(find=lambda _: self.git)

    def test_different_and_unset_preferences_pass_without_writes(self):
        self.config.write_text('# preserved comment\n[init]\n defaultBranch = student-choice\n[fetch]\n prune = no\n[credential]\n helper = fixture-helper\n')
        before = self.config.read_bytes()
        result = self.check()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['scope'], 'globalOutsideRepository')
        self.assertEqual([p['status'] for p in result['preferences']], ['different', 'different', 'unset'])
        self.assertEqual(result['preferences'][1]['value'], 'false')
        self.assertEqual(self.config.read_bytes(), before)
        self.assertNotIn('fixture-helper', str(result))

    def test_absent_file_and_empty_values_are_not_fabricated_defaults(self):
        result = self.check()
        self.assertEqual(result['status'], 'passed')
        self.assertTrue(all(p['status'] == 'unset' and p['value'] is None for p in result['preferences']))
        self.assertFalse(self.config.exists())
        self.config.write_text('[init]\n defaultBranch =\n')
        result = self.check()
        self.assertEqual(result['preferences'][0]['value'], '')
        self.assertEqual(result['preferences'][0]['status'], 'different')

    def test_boolean_equivalents_are_read_by_git(self):
        for value in ('true', 'yes', 'on', '1', ''):
            self.config.write_text('[fetch]\n prune' + (' = ' + value if value else '') + '\n')
            result = self.check()
            self.assertEqual(result['status'], 'passed', value)
            self.assertEqual(result['preferences'][1]['status'], 'matches', value)
        for value in ('false', 'no', 'off', '0'):
            self.config.write_text('[fetch]\n prune = ' + value + '\n')
            self.assertEqual(self.check()['preferences'][1]['value'], 'false')

    def test_malformed_global_system_and_invalid_boolean_are_incomplete(self):
        for path, text in ((self.config, '[broken'), (self.system, '[broken'),
                           (self.config, '[fetch]\n prune = not-a-bool\n')):
            self.config.write_text('')
            self.system.write_text('')
            path.write_text(text)
            result = self.check()
            self.assertEqual(result['status'], 'incomplete')
            self.assertEqual(result['reason'], 'configReadFailed')
            self.assertEqual(path.read_text(), text)

    def test_global_includes_are_read_without_claiming_project_effective_values(self):
        included = self.root / 'included.gitconfig'
        included.write_text('[fetch]\n prune = yes\n')
        self.config.write_text(f'[include]\n path = {included.as_posix()}\n[init]\n defaultBranch = student\n')
        project = self.root / 'project'
        subprocess.run([self.git, 'init', '--quiet', str(project)], check=True, capture_output=True)
        subprocess.run([self.git, '-C', str(project), 'config', 'fetch.prune', 'false'], check=True)
        before = (project / '.git/config').read_bytes()
        with patch.dict(os.environ, {'GIT_DIR': str(project / '.git'), 'GIT_WORK_TREE': str(project)}):
            result = self.check()
            self.assertEqual(os.environ['GIT_DIR'], str(project / '.git'))
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['preferences'][1]['value'], 'true')
        self.assertEqual((project / '.git/config').read_bytes(), before)

    def test_missing_failed_and_unavailable_command_are_distinct(self):
        self.assertEqual(git_preferences.verify(find=lambda _: None)['status'], 'notFound')
        for code, status in ((7, 'unusable'), (-1, 'incomplete')):
            result = git_preferences.verify(find=lambda _: self.git, run=lambda args, _: git_preferences.Probe(code if '--version' in args else 1))
            self.assertEqual(result['status'], status)

    def test_project_conditional_include_is_not_claimed_as_global_effective_value(self):
        project = self.root / 'conditional-project'
        subprocess.run([self.git, 'init', '--quiet', str(project)], check=True, capture_output=True)
        included = self.root / 'conditional.gitconfig'
        included.write_text('[init]\n defaultBranch = project-choice\n')
        self.config.write_text('[init]\n defaultBranch = student-choice\n' +
                               f'[includeIf "gitdir:{project.as_posix()}/.git"]\n path = {included.as_posix()}\n')
        with patch.dict(os.environ, {'GIT_DIR': str(project / '.git'), 'GIT_WORK_TREE': str(project)}):
            result = self.check()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['preferences'][0]['value'], 'student-choice')
        effective = subprocess.run([self.git, '-C', str(project), 'config', '--get', 'init.defaultBranch'], check=True, capture_output=True, text=True)
        self.assertEqual(effective.stdout.strip(), 'project-choice')

    def test_read_failure_never_becomes_unset_or_pass(self):
        for code in (7, -1):
            def query(arguments, directory):
                return git_preferences.Probe(0, 'git version 2.43.0\n') if '--version' in arguments else git_preferences.Probe(code)
            result = git_preferences.verify(find=lambda _: self.git, run=query)
            self.assertEqual(result['status'], 'incomplete')
            self.assertTrue(all(p['status'] == 'unreadable' for p in result['preferences']))

    @unittest.skipUnless(os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() != 0,
                         'Unprivileged POSIX permission fixture')
    def test_actual_access_denied_is_incomplete_and_preserves_file(self):
        self.config.write_text('[init]\n defaultBranch = student-choice\n')
        before = self.config.read_bytes()
        self.config.chmod(0)
        try:
            self.assertEqual(self.check()['status'], 'incomplete')
        finally:
            self.config.chmod(0o600)
        self.assertEqual(self.config.read_bytes(), before)
        included = self.root / 'unreadable-include.gitconfig'
        included.write_text('[fetch]\n prune = yes\n')
        self.config.write_text(f'[include]\n path = {included.as_posix()}\n')
        included.chmod(0)
        try:
            self.assertEqual(self.check()['status'], 'incomplete')
        finally:
            included.chmod(0o600)

    def test_report_and_real_validator_fragment_count_one_required_result(self):
        import contextlib
        import io
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(git_preferences.report(self.check()), 0)
        self.assertEqual(output.getvalue().count('SKYVIEW_EVENT|validation|PASS|Git:'), 1)
        self.assertNotIn('WARNING', output.getvalue())
        if os.name != 'posix':
            return
        source = (ROOT / 'linux/Validate-SkyviewStudentDev.sh').read_text()
        fragment = source[source.index('GIT_PREFERENCES='):source.index('if [[ "${1:-}" == "--check-updates"')]
        program = 'PASS_COUNT=0; FAIL_COUNT=0\ninfo() { :; }; fail() { FAIL_COUNT=$((FAIL_COUNT+1)); }\n' + fragment + '\nprintf "COUNTS %s %s\\n" "$PASS_COUNT" "$FAIL_COUNT"'
        result = subprocess.run(['/bin/bash', '-c', program], env={**os.environ, 'SCRIPT_DIR': str(ROOT / 'linux')}, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('COUNTS 1 0', result.stdout)

class ToolMetadata(unittest.TestCase):
    def test_node_uses_approved_family_when_latest_is_26(self):
        with patch.object(tools, "command", return_value="nodejs | 26.0.0 | source\nnodejs | 24.21.0 | source"):
            self.assertEqual(tools.candidate_for("nodejs"), "24.21.0")

    def test_python_rejects_new_runtime_family(self):
        with patch.object(tools, "command", return_value="Candidate: 3.15.0"):
            self.assertIsNone(tools.candidate_for("python3.14"))

    def node_records(self, tracked, selected='24.19.0', snapshot=False):
        def command(*args):
            if args[0] == 'dpkg-query' and args[-1] == 'nodejs':
                return 'installed\t' + tracked if tracked else None
            if args[0] == 'apt-cache' and args[-1] == 'nodejs':
                return 'nodejs | 24.21.0-1nodesource1 | approved'
            if args[:2] == ('dpkg', '--compare-versions'):
                return ''
            return None
        with patch.object(tools, 'command', side_effect=command) as commands:
            records = {r['tool']: r for r in tools.records(True,
                       snapshot={'Node.js': selected, 'npm': '11.9.0'} if snapshot else None,
                       node=dict(status='passed', version=selected, npmVersion='11.9.0'))}
        self.assertFalse(any(call.args[0] == 'npm' for call in commands.call_args_list))
        return records

    def test_node_selected_runtime_cannot_borrow_another_packages_update(self):
        for tracked in ('24.18.0-1nodesource1', '24.20.0-1nodesource1', '26.0.0-1', None):
            for snapshot in (False, True):
                with self.subTest(tracked=tracked, snapshot=snapshot):
                    records = self.node_records(tracked, snapshot=snapshot)
                    self.assertEqual(records['Node.js']['installedVersion'], '24.19.0')
                    self.assertEqual(records['npm']['installedVersion'], '11.9.0')
                    self.assertEqual(records['Node.js']['updateCheck'], 'native')
                    self.assertEqual(records['Node.js']['updateReason'], 'maintenanceUnverified')
                    self.assertFalse(records['Node.js']['updateAvailable'])
                    self.assertIsNone(records['Node.js']['availableVersion'])

    def test_matching_node_package_version_can_supply_advisory_metadata(self):
        for tracked in ('24.19.0-1nodesource1', '1:24.19.0+dfsg-1'):
            records = self.node_records(tracked)
            self.assertEqual(records['Node.js']['updateCheck'], 'current')
            self.assertEqual(records['Node.js']['availableVersion'], '24.21.0-1nodesource1')

    def test_failed_pair_does_not_supply_installed_npm_from_default(self):
        with patch.object(tools, 'command', return_value=None) as commands:
            records = {r['tool']: r for r in tools.records(False, node=dict(status='unusable', version='24.19.0'))}
        self.assertIsNone(records['Node.js']['installedVersion'])
        self.assertIsNone(records['npm']['installedVersion'])
        self.assertFalse(any(call.args[0] == 'npm' for call in commands.call_args_list))

    def test_update_comparison_and_unknown_candidate(self):
        def command(*args):
            if args[0] == "dpkg-query":
                return "installed\t2.43.0" if args[-1] == "git" else None
            if args[0] == "apt-cache":
                return "Candidate: 2.44.0" if args[-1] == "git" else "Candidate: (none)"
            if args[0] == "dpkg":
                return ""
            return None
        with patch.object(tools, "command", side_effect=command), patch.object(Path, "read_text", side_effect=OSError()):
            records = {r["tool"]: r for r in tools.records(True)}
        self.assertTrue(records["Git"]["updateAvailable"])
        self.assertEqual(records["Git"]["availableVersion"], "2.44.0")
        self.assertEqual(records["Firefox"]["updateCheck"], "native")
        self.assertEqual(records["Firefox"]["updateReason"], "applicationMaintenanceUnverified")
        self.assertFalse(records["Firefox"]["updateAvailable"])

    def test_skipped_check_does_not_query_available_versions(self):
        with patch.object(tools, "command", return_value=None) as command, patch.object(Path, "read_text", side_effect=OSError()), patch.object(tools.urllib.request, "urlopen") as network:
            records = list(tools.records(False))
        self.assertFalse(any(args[0][0] == "apt-cache" for args in command.call_args_list))
        network.assert_not_called()
        self.assertTrue(all(not r["updateAvailable"] for r in records))

class ComparisonAvailability(unittest.TestCase):
    def test_unknown_comparator_never_means_current(self):
        def command(*args):
            return "Candidate: 2.44.0" if args[0] == "apt-cache" else None
        with patch.object(tools, "command", side_effect=command):
            records = {r["tool"]: r for r in tools.records(True, {"Git": "2.43.0"})}
        self.assertEqual(records["Git"]["updateCheck"], "unavailable")
        self.assertFalse(records["Git"]["updateAvailable"])

class ScheduleMetadata(unittest.TestCase):
    timer = dict(LoadState="loaded", UnitFileState="enabled", ActiveState="active", Persistent="yes",
                 TimersCalendar="{ OnCalendar=Sun *-*-* 03:00:00 ; next_elapse=ignored }",
                 RandomizedDelayUSec="1h", NextElapseUSecRealtime="Sun 2026-10-11 10:00:00 UTC")
    service = dict(LoadState="loaded", ActiveState="inactive", Result="success", ExecMainStatus="0",
                   ExecMainStartTimestamp="Sun 2026-10-04 10:00:00 UTC")
    def inspect(self, timer=None, service=None):
        with patch.object(schedule, "show", side_effect=[timer or self.timer, service or self.service]):
            return schedule.inspect()

    def test_success_timestamp_catchup_and_actual_calendar(self):
        result = self.inspect()
        self.assertEqual(result["lastResult"], "success")
        self.assertEqual(result["lastRun"], "2026-10-04T10:00:00+00:00")
        self.assertTrue(result["catchUp"])
        self.assertIn("Sun *-*-* 03:00:00", result["frequency"])
        self.assertIn("1h", result["frequency"])

    def test_disabled_timer_and_failed_service_are_independent(self):
        result = self.inspect({**self.timer, "UnitFileState": "disabled", "ActiveState": "inactive"}, {**self.service, "Result": "exit-code", "ExecMainStatus": "1"})
        self.assertEqual(result["status"], "disabled")
        self.assertIsNone(result["nextRun"])
        self.assertEqual(result["lastResult"], "failure")

    def test_busy_maintenance_is_deferred_and_not_success(self):
        result = self.inspect(service={**self.service, "Result": "exit-code", "ExecMainStatus": "75"})
        self.assertEqual(result["lastResult"], "deferred")

    def test_never_run_vs_lost_history_after_restart(self):
        service = {**self.service, "ExecMainStartTimestamp": ""}
        self.assertEqual(self.inspect(service=service)["lastResult"], "never")
        result = self.inspect({**self.timer, "LastTriggerUSec": "Sun 2026-10-04 10:00:00 UTC"}, service)
        self.assertEqual(result["lastResult"], "unavailable")
        self.assertIsNotNone(result["lastRun"])

    def test_running_missing_and_read_error(self):
        self.assertEqual(self.inspect(service={**self.service, "ActiveState": "activating"})["lastResult"], "running")
        with patch.object(schedule, "show", return_value={"LoadState": "not-found"}):
            self.assertEqual(schedule.inspect()["status"], "missing")
        with patch.object(schedule, "show", side_effect=OSError("Read denied")):
            result = schedule.inspect()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["lastResult"], "unavailable")
        self.assertIn("Read denied", result["note"])

class EditorPreferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node_runtime = module('node_runtime')
        cls.editor = module('editor_preferences')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sde editor café ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'settings with spaces.json'
        self.node = shutil.which('node')
        self.assertIsNotNone(self.node, 'Prepared Node 24 is required')
        self.node_record = dict(version='24.19.0', executable=self.node)

    def check(self, text):
        self.path.write_text(text, encoding='utf-8')
        before = self.path.read_bytes()
        result = self.editor.verify(self.path, self.node_record)
        self.assertEqual(self.path.read_bytes(), before)
        return result

    def test_comments_trailing_commas_customizations_and_override_scope(self):
        result = self.check('// retain this\n{"editor.formatOnSave":false, "editor.defaultFormatter":"student.formatter", "files.eol":"\\r\\n", "[python]":{"editor.formatOnSave":true,},"private-fixture":"do-not-export",}')
        self.assertEqual(result['status'], 'read', result)
        self.assertEqual(result['scope'], 'standardUserFile')
        self.assertTrue(all(row['status'] == 'different' for row in result['recommendations']))
        self.assertNotIn('do-not-export', str(result))
        self.assertEqual(result['recommendations'][0]['value'], False)

    def test_missing_empty_bom_and_comment_only_settings_are_defaults_not_breakage(self):
        missing = self.editor.verify(self.path, None)
        self.assertEqual((missing['status'], missing['reason']), ('missing', 'defaults'))
        self.assertFalse(self.path.exists())
        for text in ('', '  \n', '/* keep my defaults */\n// and this comment', '\ufeff{}'):
            with self.subTest(text=text):
                result = self.check(text)
                self.assertEqual(result['status'], 'read', result)
                self.assertTrue(all(row['status'] == 'unset' for row in result['recommendations']))

    def test_parser_errors_cannot_supply_a_fault_tolerant_partial_pass(self):
        for text in ('{"editor.formatOnSave":true, "broken"}', '{', '{"a":1} garbage',
                     '/* unterminated', '{"a":"\\q"}', '[]', 'false', 'null'):
            with self.subTest(text=text):
                result = self.check(text)
                self.assertEqual((result['status'], result['reason']), ('invalid', 'invalidContents'))
                self.assertEqual(result['recommendations'], [])

    def test_values_are_bounded_and_own_keys_are_used(self):
        result = self.check('{"__proto__":{"editor.formatOnSave":true},"editor.defaultFormatter":' + __import__('json').dumps('x' * 300) + '}')
        self.assertEqual(result['status'], 'read')
        self.assertEqual(result['recommendations'][0]['status'], 'unset')
        self.assertEqual(result['recommendations'][1]['status'], 'different')
        self.assertIsNone(result['recommendations'][1]['value'])

    def test_parser_unavailable_is_not_malformed_or_missing(self):
        result = self.check('{}')
        self.assertEqual(result['status'], 'read')
        unknown = self.editor.verify(self.path, None)
        self.assertEqual((unknown['status'], unknown['reason']), ('unavailable', 'parserUnavailable'))
        for probe in (self.node_runtime.Probe(7), self.node_runtime.Probe(-1, reason='timeout'), self.node_runtime.Probe(0, '{broken')):
            result = self.editor.verify(self.path, self.node_record, run=lambda *_: probe)
            self.assertEqual(result['status'], 'unavailable')
        script = self.root / 'without-parser.cjs'
        shutil.copyfile(ROOT / 'linux/lib/editor_settings_probe.cjs', script)
        result = subprocess.run([self.node, str(script), str(self.path)], check=True, capture_output=True, text=True, timeout=5)
        import json
        record = json.loads(result.stdout)
        self.assertEqual((record['status'], record['reason']), ('unavailable', 'parserUnavailable'))

    @unittest.skipUnless(os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() != 0,
                         'Unprivileged POSIX access fixture')
    def test_actual_access_denied_does_not_fail_required_editor_features(self):
        self.path.write_text('{}')
        self.path.chmod(0)
        try:
            result = self.editor.verify(self.path, self.node_record)
        finally:
            self.path.chmod(0o600)
        self.assertEqual((result['status'], result['reason']), ('unreadable', 'accessDenied'))
        import contextlib, io
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = self.editor.report(result)
        self.assertEqual(code, 20)
        self.assertIn('SKYVIEW_EVENT|validation|WARNING|', output.getvalue())
        self.assertNotIn('SKYVIEW_EVENT|validation|FAIL|', output.getvalue())

    def test_large_and_non_utf8_files_stay_distinct(self):
        self.path.write_bytes(b'x' * 1048577)
        self.assertEqual(self.editor.verify(self.path, self.node_record)['reason'], 'inspectionLimit')
        self.path.write_bytes(b'\xff\xfe\x00')
        self.assertEqual(self.editor.verify(self.path, self.node_record)['reason'], 'encodingUnavailable')
        self.path.unlink()
        self.path.mkdir()
        self.assertEqual(self.editor.verify(self.path, self.node_record)['status'], 'unreadable')

    def test_observation_decoder_rejects_false_passes_and_authority(self):
        import json
        good = self.check('{"editor.formatOnSave":true}')
        for patch_value in ({'schema': True}, {'scope': 'allProjects'}, {'status': 'passed'},
                            {'path': '/other/settings.json'}, {'permission': 'repair'},
                            {'reason': 'defaults'}, {'recommendations': []}):
            self.assertIsNone(self.editor.observation(json.dumps({**good, **patch_value}), str(self.path)))

    def test_pinned_parser_and_both_helper_copies_match(self):
        import hashlib, json
        lock = json.loads((ROOT / 'installer/package-lock.json').read_text())
        self.assertEqual(lock['packages']['']['devDependencies']['jsonc-parser'], '3.3.1')
        self.assertEqual(lock['packages']['node_modules/jsonc-parser']['integrity'], 'sha512-HUgH65KyejrUFPvHFPbqOY0rsFip3Bo5wb4ngvdi1EpCYWUQDC5V+Y7mZws+DLkr4M//zQJoanu1SP+87Dv1oQ==')
        expected = {'parser.js':'a35db1bfb9631dcba643fa42972e9ebe2a318b4de3cac239d29081577a43d688',
                    'scanner.js':'581d82c4f1aa84b0605369c01f414fb0164ee462e03daa298cb960076a2a9e82',
                    'LICENSE.md':'c3a24c02d678e5f0711623dcf3ab3f243b273c2633f638a1fa8e35fb7c7f8e4d'}
        for platform in ('linux/lib', 'windows/chocolatey/tools'):
            for name, digest in expected.items():
                self.assertEqual(hashlib.sha256((ROOT / platform / 'jsonc-parser' / name).read_bytes()).hexdigest(), digest)
        self.assertEqual((ROOT / 'linux/lib/editor_settings_probe.cjs').read_bytes(), (ROOT / 'windows/chocolatey/tools/EditorSettingsProbe.cjs').read_bytes())

    def test_real_optional_validator_fragment_counts_warning_not_failure(self):
        import json
        if os.name != 'posix':
            return
        config = self.root / 'xdg/VSCodium/User/settings.json'
        config.parent.mkdir(parents=True)
        config.write_text('{broken')
        source = (ROOT / 'linux/Validate-SkyviewStudentDev.sh').read_text()
        fragment = source[source.index('CODIUM_SETTINGS='):source.index('\nEXT_FILE=')]
        program = 'WARN_COUNT=0; FAIL_COUNT=0\nwarnv() { WARN_COUNT=$((WARN_COUNT+1)); }\n' + fragment + '\nprintf "COUNTS %s %s\\n" "$WARN_COUNT" "$FAIL_COUNT"'
        result = subprocess.run(['/bin/bash', '-c', program], env={**os.environ, 'SCRIPT_DIR': str(ROOT / 'linux'),
                                'TARGET_HOME': str(self.root), 'XDG_CONFIG_HOME': str(self.root / 'xdg'), 'NODE_RECORD': json.dumps(self.node_record)},
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('COUNTS 1 0', result.stdout)
        self.assertIn('"status":"invalid"', result.stdout)



class EditorLocations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.editor = module('editor_location')

    def setUp(self):
        import json
        self.json = json
        self.temp = tempfile.TemporaryDirectory(prefix='sde editor location café ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.exe = self.root / 'codium'
        self.exe.write_bytes(b'\x7fELFfixture-never-executed')
        self.exe.chmod(0o700)
        (self.root / 'resources/app/out').mkdir(parents=True)
        (self.root / self.editor.FILES[0]).write_text(json.dumps(dict(nameShort='VSCodium', applicationName='codium', quality='stable')))
        (self.root / self.editor.FILES[1]).write_text('{"version":"1.106.0.25351"}')
        (self.root / self.editor.FILES[2]).write_text('// fixture, never executed')
        self.record = dict(self.editor.empty_record(), status='candidate', reason='identityObserved', root=str(self.root),
                           executable=str(self.exe), cli=str(self.root / self.editor.FILES[2]), version='1.106.0.25351',
                           electronVersion='38.0.0', selectionId=self.editor.selection_id(self.root))
        normal = patch.object(self.editor, 'normal_user', return_value=True)
        normal.start()
        self.addCleanup(normal.stop)

    def inspect(self, version=None, find=None, identity=None):
        calls = []
        def run(arguments, timeout):
            self.assertGreater(timeout, 0)
            calls.append(arguments)
            return ((identity or self.editor.Probe(0, self.json.dumps(self.record))) if len(calls) == 1
                    else version or self.editor.Probe(0, self.record['version'] + '\nfixture-commit\nx64'))
        value = self.editor.inspect(run=run, find=find or (lambda: ([str(self.root)], True, 'discoveryIncomplete')))
        return value, calls

    def test_alternate_installation_spaces_and_same_cli_selected(self):
        before = {p: p.read_bytes() for p in [self.exe, *[self.root / f for f in self.editor.FILES]]}
        value, calls = self.inspect()
        self.assertEqual(value['status'], 'verified')
        self.assertEqual(value['selectionId'], self.record['selectionId'])
        self.assertEqual(calls[1], [str(self.exe), self.record['cli'], '--version'])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(value['maintenanceEligibility'], 'notEvaluated')

    def test_failed_or_invalid_version_never_passes(self):
        for code, text in [(7, self.record['version']), (0, 'not a version'), (0, '1.105.0'), (-1, '')]:
            with self.subTest(code=code, text=text):
                value, _ = self.inspect(version=self.editor.Probe(code, text))
                self.assertNotEqual(value['status'], 'verified')
                self.assertIsNone(value['selectionId'])

    def test_malformed_or_unexpected_identity_is_not_authority(self):
        for text in ['{}', 'not JSON', self.json.dumps(dict(self.record, extra=True)),
                     self.json.dumps(dict(self.record, selectionId='0' * 64)),
                     self.json.dumps(dict(self.record, electronVersion='')), self.json.dumps(dict(self.record, schema=True))]:
            value, calls = self.inspect(identity=self.editor.Probe(0, text))
            self.assertEqual(value['status'], 'incomplete')
            self.assertEqual(len(calls), 1)

    def test_wrong_product_and_non_native_target_never_executed(self):
        (self.root / self.editor.FILES[0]).write_text('{"nameShort":"Another editor"}')
        value, calls = self.inspect()
        self.assertEqual(value['status'], 'unusable')
        self.assertEqual(calls, [])
        self.exe.write_text('#!/bin/sh\nexit 0\n')
        value, calls = self.inspect()
        self.assertEqual(value['status'], 'unusable')
        self.assertEqual(calls, [])

    def test_missing_and_incomplete_search_are_distinct(self):
        for complete, status in [(True, 'notFound'), (False, 'incomplete')]:
            value, calls = self.inspect(find=lambda: ([], complete, 'staleRegistration'))
            self.assertEqual(value['status'], status)
            self.assertEqual(calls, [])
        with patch.object(self.editor, 'metadata', side_effect=PermissionError):
            value, calls = self.inspect()
        self.assertEqual(value['reason'], 'accessDenied')
        self.assertEqual(value['status'], 'incomplete')
        self.assertEqual(calls, [])

    def test_no_elevated_external_probe(self):
        with patch.object(self.editor, 'normal_user', return_value=False):
            value, calls = self.inspect(find=lambda: self.fail('must not discover as root'))
        self.assertEqual(value['reason'], 'normalUserRequired')
        self.assertEqual(calls, [])

    def test_changed_installation_during_version_check_stays_incomplete(self):
        def run(arguments, timeout):
            if arguments[-1] == '--version':
                (self.root / self.editor.FILES[2]).write_text('changed')
                return self.editor.Probe(0, self.record['version'])
            return self.editor.Probe(0, self.json.dumps(self.record))
        result = self.editor.inspect(run=run, find=lambda: ([str(self.root)], True, 'discoveryIncomplete'))
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['reason'], 'changedDuringCheck')

    def test_resource_symlink_escape_rejected_before_execution(self):
        external = self.root / 'outside.js'
        external.write_text('fixture')
        cli = self.root / self.editor.FILES[2]
        cli.unlink()
        cli.symlink_to(external)
        value, calls = self.inspect()
        self.assertEqual(value['status'], 'unusable')
        self.assertEqual(calls, [])

    def test_desktop_records_are_paths_not_shell_commands_or_profiles(self):
        parse = self.editor.desktop_executable
        self.assertEqual(parse('[Desktop Entry]\nExec="/home/student/My Editor/bin/codium" --unity-launch %F\n'), '/home/student/My Editor/bin/codium')
        for command in ['env codium', '/bin/sh -c codium', 'codium %F', '"/opt/codium" --user-data-dir /tmp/profile',
                        '"/opt/codium"; touch /tmp/no', '/opt/codium $(echo command)']:
            self.assertIsNone(parse('[Desktop Entry]\nExec=' + command))
        self.assertIsNone(parse('[Desktop Entry]\nExec=/opt/codium\nExec=/other/codium'))

    def test_actual_cjs_snapshot_agrees_and_regular_node_is_not_electron(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Prepared Node required for probe fixture')
        probe = ROOT / 'linux/lib/editor_identity.cjs'
        result = subprocess.run([node, '-e', 'console.log(JSON.stringify(require(process.argv[1]).snapshot(process.argv[2], "38.0.0")))',
                                 str(probe), str(self.exe)], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.json.loads(result.stdout), self.record)
        result = subprocess.run([node, str(probe)], capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_failed_extension_listing_cannot_supply_partial_required_pass(self):
        from contextlib import redirect_stdout
        from io import StringIO
        policy = self.root / 'extensions.txt'
        policy.write_text('required.extension\n')
        output = StringIO()
        with patch.object(self.editor, 'inspect', return_value=dict(self.record, status='verified', reason='verified')), \
             patch.object(self.editor, 'query', return_value=self.editor.Probe(7, 'required.extension')), redirect_stdout(output):
            code = self.editor.validation(str(policy))
        self.assertEqual(code, 10)
        self.assertNotIn('PASS|VSCodium extension', output.getvalue())
        self.assertIn('FAIL|VSCodium:', output.getvalue())

    def test_selected_version_never_grants_package_update_authority(self):
        selected = dict(self.record, status='verified', reason='verified')
        with patch.object(tools, 'command', return_value=None):
            result = next(r for r in tools.records(True, editor=selected) if r['tool'] == 'VSCodium')
        self.assertEqual(result['installedVersion'], self.record['version'])
        self.assertFalse(result['updateAvailable'])
        self.assertEqual(result['updateReason'], 'applicationMaintenanceUnverified')
        self.assertEqual(result['updateCheck'], 'native')

    def test_discovery_uses_registered_paths_and_marks_stale_records_incomplete(self):
        link = self.root / 'bin/codium'
        link.parent.mkdir()
        link.symlink_to(self.exe)
        data = self.root / 'xdg'
        (data / 'applications').mkdir(parents=True)
        desktop = data / 'applications/codium.desktop'
        desktop.write_text(f'[Desktop Entry]\nExec="{link}" %F\n')
        with patch.dict(os.environ, {'HOME': str(self.root), 'XDG_DATA_HOME': str(data), 'XDG_DATA_DIRS': str(self.root / 'system-data')}), \
             patch.object(self.editor.shutil, 'which', return_value=str(link)):
            roots, complete, _ = self.editor.discover()
            self.assertEqual(roots[0], str(self.root))
            self.assertEqual(roots.count(str(self.root)), 1)
            self.assertTrue(complete)
            desktop.write_text(f'[Desktop Entry]\nExec="{self.root}/missing/codium" %F\n')
            _, complete, reason = self.editor.discover()
            self.assertFalse(complete)
            self.assertEqual(reason, 'staleRegistration')

    def test_diagnostic_query_bounds_and_cleans_environment(self):
        with patch.dict(os.environ, {'NODE_OPTIONS': '--require malicious.cjs', 'VSCODE_DEV': '1'}):
            result = self.editor.query([sys.executable, '-c', 'import os; print(os.getenv("NODE_OPTIONS"), os.getenv("VSCODE_DEV"), os.getenv("ELECTRON_RUN_AS_NODE"))'], 2)
        self.assertEqual(result.code, 0)
        self.assertEqual(result.text, 'None None 1')
        self.assertEqual(self.editor.query([sys.executable, '-c', 'print("x" * 40000)'], 2).code, -1)
        self.assertEqual(self.editor.query([sys.executable, '-c', 'import time; time.sleep(3)'], .1).code, -1)

    def test_validator_cannot_succeed_with_empty_collector_output(self):
        lib = self.root / 'lib'
        lib.mkdir()
        helper = lib / 'editor_location.py'
        helper.write_text('')
        source = (ROOT / 'linux/Validate-SkyviewStudentDev.sh').read_text()
        fragment = source[source.index('EXT_FILE='):source.index('\n# Scheduling is observed')]
        program = 'FAIL_COUNT=0; PASS_COUNT=0\nfail() { FAIL_COUNT=$((FAIL_COUNT+1)); }\n' + fragment + '\nprintf "COUNTS %s %s\\n" "$PASS_COUNT" "$FAIL_COUNT"'
        result = subprocess.run(['/bin/bash', '-c', program], env={**os.environ, 'SKYVIEW_SHARE': str(self.root),
                                'SCRIPT_DIR': str(self.root), 'SKYVIEW_LIB': str(lib)}, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('COUNTS 0 1', result.stdout)


class PyCharmLocations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        module('editor_location')
        cls.app = module('pycharm_location')

    def setUp(self):
        import json
        self.json = json
        self.temp = tempfile.TemporaryDirectory(prefix='sde PyCharm alternate ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'bin').mkdir()
        (self.root / 'jbr/bin').mkdir(parents=True)
        self.launcher = self.root / 'bin/pycharm'
        self.runtime = self.root / 'jbr/bin/java'
        for file in (self.launcher, self.runtime):
            file.write_bytes(b'\x7fELF\x02\x01' + b'\x00' * 12 + b'\x3e\x00' + b'fixture-never-executed')
            file.chmod(0o700)
        self.info = dict(name='PyCharm', productCode='PY', version='2026.1.1', minRequiredJavaVersion=21, launch=[dict(os='Linux', arch='amd64', launcherPath='bin/pycharm', javaExecutablePath='jbr/bin/java')])
        self.metadata = self.root / 'product-info.json'
        self.metadata.write_text(json.dumps(self.info))
        for target, value in [('normal_user', True)]:
            p = patch.object(self.app, target, return_value=value)
            p.start(); self.addCleanup(p.stop)
        p = patch.object(self.app.platform, 'machine', return_value='x86_64')
        p.start(); self.addCleanup(p.stop)
        self.calls = []

    def inspect(self, result=None, complete=True, roots=None):
        def run(args, timeout):
            self.calls.append(args)
            self.assertGreater(timeout, 0)
            return result or type('Probe', (), dict(code=0, text='openjdk 21.0.7 2025-04-15\nOpenJDK Runtime Environment JBR-21.0.7+6'))()
        return self.app.inspect(run=run, find=lambda: (roots if roots is not None else [str(self.root)], [], complete))

    def test_alternate_bundle_and_own_runtime_verified_without_managed_link(self):
        before = {p: p.read_bytes() for p in (self.metadata, self.launcher, self.runtime)}
        value = self.inspect()
        self.assertEqual(value['status'], 'verified')
        self.assertEqual(value['version'], '2026.1.1')
        self.assertEqual(self.calls, [[str(self.runtime), '--version']])
        self.assertEqual(value['maintenanceEligibility'], 'notEvaluated')
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_wrong_product_and_escaped_runtime_are_not_executed(self):
        self.metadata.write_text(self.json.dumps(dict(self.info, productCode='IU')))
        self.assertEqual(self.inspect()['status'], 'unusable')
        self.assertEqual(self.calls, [])
        self.metadata.write_text(self.json.dumps(self.info))
        self.runtime.unlink(); self.runtime.symlink_to(self.launcher)
        self.assertEqual(self.inspect()['status'], 'incomplete')
        self.assertEqual(self.calls, [])

    def test_failed_partial_or_non_bundled_runtime_output_does_not_pass(self):
        for code, text in [(7, 'openjdk 21.0.7\nJBR-21'), (0, 'openjdk 21.0.7'), (0, 'not a runtime'), (-1, '')]:
            result = type('Probe', (), dict(code=code, text=text))()
            self.assertNotEqual(self.inspect(result)['status'], 'verified')

    def test_vendor_minimum_runtime_is_required_when_present(self):
        result = type('Probe', (), dict(code=0, text='openjdk 17.0.9\nJBR-17'))()
        self.assertEqual(self.inspect(result=result)['status'], 'unusable')
        self.info.pop('minRequiredJavaVersion')
        self.metadata.write_text(self.json.dumps(self.info))
        self.assertEqual(self.inspect(result=result)['status'], 'verified')

    def test_missing_and_incomplete_search_remain_distinct(self):
        self.assertEqual(self.inspect(roots=[])['status'], 'notFound')
        self.assertEqual(self.inspect(roots=[], complete=False)['status'], 'incomplete')
        with patch.object(self.app, 'normal_user', return_value=False):
            self.assertEqual(self.inspect()['reason'], 'normalUserRequired')
        self.assertEqual(self.calls, [])

    def test_access_denial_and_disappearance_stay_incomplete(self):
        with patch.object(self.app, 'layout', side_effect=PermissionError):
            self.assertEqual(self.inspect()['reason'], 'accessDenied')
        self.runtime.unlink()
        self.assertEqual(self.inspect()['reason'], 'staleRegistration')
        self.assertEqual(self.calls, [])

    def test_changed_files_during_runtime_probe_do_not_pass(self):
        def run(args, timeout):
            self.launcher.write_bytes(b'changed')
            return type('Probe', (), dict(code=0, text='openjdk 21.0.7\nJBR-21'))()
        value = self.app.inspect(run=run, find=lambda: ([str(self.root)], [], True))
        self.assertEqual(value['reason'], 'changedDuringCheck')
        self.assertEqual(value['status'], 'incomplete')

    def test_community_and_script_launcher_supported_without_running_launcher(self):
        self.info.update(name='PyCharm Community Edition', productCode='PC')
        self.info['launch'][0]['launcherPath'] = 'bin/pycharm.sh'
        launcher = self.root / 'bin/pycharm.sh'
        launcher.write_text('#!/bin/sh\nexit 99\n'); launcher.chmod(0o700)
        self.metadata.write_text(self.json.dumps(self.info))
        self.assertEqual(self.inspect()['status'], 'verified')
        self.assertEqual(self.calls, [[str(self.runtime), '--version']])

    def test_pyCharm_selection_does_not_grant_update_ownership(self):
        selected = self.inspect()
        with patch.object(tools, 'command', return_value=None), patch.object(tools.urllib.request, 'urlopen') as network:
            record = next(r for r in tools.records(True, pycharm=selected) if r['tool'] == 'PyCharm')
        self.assertEqual(record['installedVersion'], '2026.1.1')
        self.assertFalse(record['updateAvailable'])
        self.assertEqual(record['updateReason'], 'applicationMaintenanceUnverified')
        network.assert_not_called()


class ApplicationLocations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        module('editor_location'); module('pycharm_location')
        cls.app = module('application_locations')

    def setUp(self):
        import json, zipfile
        self.json = json
        self.temp = tempfile.TemporaryDirectory(prefix='sde alternate apps ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.paths = {name: self.root / name for name in self.app.TOOLS}
        for name, path in self.paths.items():
            path.mkdir()
            self.native(path / {'DBeaver': 'dbeaver', 'Chrome': 'chrome', 'Firefox': 'firefox'}[name])
        dbeaver = self.paths['DBeaver']
        (dbeaver / 'plugins').mkdir()
        self.jar = dbeaver / 'plugins/org.jkiss.dbeaver.launcher_1.0.0.jar'
        with zipfile.ZipFile(self.jar, 'w') as archive:
            archive.writestr('META-INF/MANIFEST.MF', 'Bundle-SymbolicName: org.jkiss.dbeaver.launcher;singleton:=true\n')
        (dbeaver / '.eclipseproduct').write_text('name=DBeaver\nid=org.jkiss.dbeaver.product\nversion=26.2.1\n')
        (dbeaver / 'dbeaver.ini').write_text('-startup\nplugins/org.jkiss.dbeaver.launcher_1.0.0.jar\n-vmargs\n-Dosgi.requiredJavaVersion=21\n')
        (dbeaver / 'jre/bin').mkdir(parents=True)
        self.native(dbeaver / 'jre/bin/java')
        (self.paths['Firefox'] / 'application.ini').write_text('[App]\nName=Firefox\nID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}\nVersion=146.0.1\n')
        p=patch.object(self.app, 'normal_user', return_value=True);p.start();self.addCleanup(p.stop)
        p=patch.object(self.app.platform, 'machine', return_value='x86_64');p.start();self.addCleanup(p.stop)
        self.calls=[]

    def native(self, file):
        file.write_bytes(b'\x7fELF\x02\x01' + b'\0'*12 + b'\x3e\0fixture-never-executed')
        file.chmod(0o700)

    def inspect(self, tool, code=0, text=None, complete=True, candidates=None):
        def run(args, timeout):
            self.calls.append(args)
            self.assertGreater(timeout, 0)
            output = {'DBeaver': 'openjdk 21.0.9 2025-10-21', 'Chrome': 'Google Chrome 143.0.7499.40', 'Firefox': 'Mozilla Firefox 146.0.1'}[tool]
            return type('Probe', (), dict(code=code, text=text if text is not None else output))()
        return self.app.inspect(tool, run=run, find=lambda _: (candidates if candidates is not None else [str(self.paths[tool])], [], complete))

    def test_each_alternate_installation_owns_its_product_checks(self):
        for tool in self.app.TOOLS:
            with self.subTest(tool=tool):
                value=self.inspect(tool)
                self.assertEqual(value['status'], 'verified')
                self.assertEqual(value['root'], str(self.paths[tool]))
                self.assertEqual(value['maintenanceEligibility'], 'notEvaluated')
                target=self.paths[tool] / ('jre/bin/java' if tool == 'DBeaver' else tool.lower())
                self.assertEqual(self.calls[-1], [str(target), '--version'])
        self.assertEqual(self.inspect('Firefox', text='Mozilla Firefox 146.0.1esr')['status'], 'verified')

    def test_wrong_browser_brand_version_or_failed_command_never_passes(self):
        for tool, code, text in [('Chrome', 0, 'Chromium 143.0.7499.40'), ('Firefox', 0, 'Mozilla Firefox 145.0'),
                                 ('Chrome', 7, 'Google Chrome 143.0.7499.40'), ('Firefox', -1, '')]:
            self.assertNotEqual(self.inspect(tool, code, text)['status'], 'verified')

    def test_internal_firefox_native_symlink_is_supported_without_escape(self):
        target=self.paths['Firefox']/'firefox'
        native=target.with_name('firefox-bin')
        target.rename(native); target.symlink_to('firefox-bin')
        self.assertEqual(self.inspect('Firefox')['status'], 'verified')
        self.assertEqual(self.calls[-1], [str(native), '--version'])
        target.unlink();target.symlink_to(self.paths['Chrome']/'chrome')
        self.assertEqual(self.inspect('Firefox')['status'], 'incomplete')

    def test_dbeaver_product_and_startup_identity_checked_before_runtime(self):
        (self.paths['DBeaver'] / '.eclipseproduct').write_text('name=Other\nid=org.jkiss.dbeaver.product\nversion=26.2.1\n')
        self.assertEqual(self.inspect('DBeaver')['status'], 'unusable')
        self.assertEqual(self.calls, [])

    def test_dbeaver_vm_minimum_and_failure_are_required(self):
        self.assertEqual(self.inspect('DBeaver', text='openjdk 17.0.9')['status'], 'unusable')
        self.assertEqual(self.inspect('DBeaver', code=7, text='openjdk 21.0.9')['status'], 'unusable')
        (self.paths['DBeaver'] / 'jre/bin/java').unlink()
        self.assertEqual(self.inspect('DBeaver')['status'], 'incomplete')

    def test_jar_escape_and_wrong_bundle_do_not_execute(self):
        (self.paths['DBeaver'] / 'dbeaver.ini').write_text('-startup\n../untrusted.jar\n')
        self.assertEqual(self.inspect('DBeaver')['status'], 'incomplete')
        self.assertEqual(self.calls, [])
        (self.paths['DBeaver'] / 'dbeaver.ini').write_text('-startup\nplugins/org.jkiss.dbeaver.launcher_1.0.0.jar\n')
        import zipfile
        with zipfile.ZipFile(self.jar, 'w') as archive:
            archive.writestr('META-INF/MANIFEST.MF', 'Bundle-SymbolicName: other.product\n')
        self.assertEqual(self.inspect('DBeaver')['status'], 'unusable')
        self.assertEqual(self.calls, [])

    def test_missing_unknown_and_elevated_states_remain_distinct(self):
        self.assertEqual(self.inspect('Chrome', candidates=[])['status'], 'notFound')
        self.assertEqual(self.inspect('Chrome', candidates=[], complete=False)['status'], 'incomplete')
        with patch.object(self.app, 'normal_user', return_value=False):
            self.assertEqual(self.inspect('Chrome')['reason'], 'normalUserRequired')
        self.assertEqual(self.calls, [])

    def test_access_denial_resource_disappearance_and_replaced_target(self):
        with patch.object(self.app, 'checked', side_effect=PermissionError):
            self.assertEqual(self.inspect('Firefox')['reason'], 'accessDenied')
        (self.paths['Firefox'] / 'application.ini').unlink()
        self.assertEqual(self.inspect('Firefox')['reason'], 'staleRegistration')
        target=self.paths['Chrome'] / 'chrome'
        def run(args, timeout):
            target.write_bytes(target.read_bytes()+b'changed')
            return type('Probe', (), dict(code=0, text='Google Chrome 143.0.7499.40'))()
        result=self.app.inspect('Chrome', run=run, find=lambda _: ([str(self.paths['Chrome'])], [], True))
        self.assertEqual(result['reason'], 'changedDuringCheck')

    def test_selected_app_versions_do_not_grant_apt_update_authority(self):
        apps={tool:self.inspect(tool) for tool in self.app.TOOLS}
        with patch.object(tools, 'command', return_value=None):
            records={r['tool']:r for r in tools.records(True, applications=apps)}
        for tool in self.app.TOOLS:
            self.assertEqual(records[tool]['installedVersion'], apps[tool]['version'])
            self.assertFalse(records[tool]['updateAvailable'])
            self.assertEqual(records[tool]['updateReason'], 'applicationMaintenanceUnverified')

    def test_unsupported_chrome_architecture_keeps_original_nonblocking_policy(self):
        with patch.object(self.app.platform, 'machine', return_value='aarch64'):
            self.assertEqual(self.inspect('Chrome')['status'], 'notApplicable')
        self.assertEqual(self.calls, [])

    def test_empty_collector_output_cannot_make_three_required_apps_pass(self):
        lib=self.root/'lib';lib.mkdir();(lib/'application_locations.py').write_text('')
        source=(ROOT/'linux/Validate-SkyviewStudentDev.sh').read_text()
        fragment=source[source.index('APPLICATION_LOCATIONS='):source.index('# One selected interpreter')]
        program='PASS_COUNT=0;FAIL_COUNT=0;WARN_COUNT=0\nfail() { FAIL_COUNT=$((FAIL_COUNT+1)); }\n'+fragment+'\nprintf "COUNTS %s %s %s\\n" "$PASS_COUNT" "$WARN_COUNT" "$FAIL_COUNT"'
        result=subprocess.run(['/bin/bash','-c',program],env={**os.environ,'SCRIPT_DIR':str(self.root),'SKYVIEW_LIB':str(lib)},capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('COUNTS 0 0 3',result.stdout)



class EditorExtensionPreservation(unittest.TestCase):
    """Execute the production Bash function with an isolated command recorder."""
    def run_profile(self, policy, inventory='', query_exit=0, fail_install='', root=False):
        import json
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            (fixture / 'extensions.txt').write_text(policy)
            cli = fixture / 'codium'
            cli.write_text("#!/usr/bin/python3\n" +
                "import json,os,sys\nfrom pathlib import Path\n" +
                "p=Path(os.environ['SDE_EXT_FIXTURE'])\n" +
                "if os.environ.get('HOME')!=str(p):sys.exit(98)\n" +
                "with (p/'calls').open('a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')\n" +
                "config=json.loads((p/'config').read_text())\n" +
                "if sys.argv[1:]==['--list-extensions']:\n print(config['inventory']);sys.exit(config['query_exit'])\n" +
                "if sys.argv[1:]==['--install-extension',config['fail_install']]:sys.exit(23)\n" +
                "if len(sys.argv)!=3 or sys.argv[1]!='--install-extension':sys.exit(42)\n")
            cli.chmod(0o755)
            (fixture / 'config').write_text(json.dumps(dict(inventory=inventory,query_exit=query_exit,fail_install=fail_install)))
            env = dict(os.environ, PATH=str(fixture)+':/usr/bin:/bin',SDE_EXT_FIXTURE=str(fixture))
            script = 'source "$1"; id(){ printf "%s\\n" '+('0' if root else '1000')+'; }; '
            if root:
                script += 'runuser(){ [[ "$1" == -u && "$2" == student && "$3" == -- ]] || exit 99; shift 3; "$@"; }; '
            script += 'install_codium_extensions_for_user student "$2" "$2/extensions.txt"'
            result=subprocess.run(['/bin/bash','-c',script,'probe',str(ROOT/'linux/lib/common.sh'),str(fixture)],env=env,capture_output=True,text=True)
            calls=[json.loads(line) for line in (fixture/'calls').read_text().splitlines()] if (fixture/'calls').exists() else []
            return result,calls

    def test_keeps_existing_case_insensitive_and_foreign_extensions(self):
        result,calls=self.run_profile('EditorConfig.EditorConfig\nesbenp.prettier-vscode\n','editorconfig.editorconfig\nesbenp.prettier-vscode\nstudent.personal-extension')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(calls,[['--list-extensions']])

    def test_installs_only_missing_and_never_forces_or_repeats_a_duplicate(self):
        result,calls=self.run_profile('keep.extension\nnew.extension\nNEW.EXTENSION\n','keep.extension')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(calls,[['--list-extensions'],['--install-extension','new.extension']])

    def test_empty_policy_does_not_query_or_install(self):
        result,calls=self.run_profile('  # no required extensions\n\n',query_exit=23)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(calls,[])

    def test_unreadable_inventory_cannot_be_treated_as_missing(self):
        result,calls=self.run_profile('new.extension\n',query_exit=23)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(calls,[['--list-extensions']])
        self.assertIn('No extensions were changed',result.stderr)

    def test_malformed_inventory_stops_before_any_installation(self):
        for inventory in ['keep.extension\nnot an extension','--install-extension anything','a.'+'x'*257]:
            with self.subTest(inventory=inventory):
                result,calls=self.run_profile('new.extension\n',inventory)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(calls,[['--list-extensions']])

    def test_policy_is_checked_completely_before_any_change(self):
        for policy in ['new.extension\nbad --argument\n','x.y\n'*257,'x'*65537]:
            with self.subTest(length=len(policy)):
                result,calls=self.run_profile(policy)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(calls,[])

    def test_installation_failure_stops_without_retrying_or_changing_later_entries(self):
        result,calls=self.run_profile('new.extension\nlater.extension\n',fail_install='new.extension')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(calls,[['--list-extensions'],['--install-extension','new.extension']])

    def test_root_path_uses_the_requested_normal_user_for_both_commands(self):
        result,calls=self.run_profile('new.extension\n',root=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(calls,[['--list-extensions'],['--install-extension','new.extension']])



class ProjectWorkingFolders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        module('editor_location')
        cls.project = module('project_location')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sde project café ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(HOME=str(self.root),GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null')
        environment=patch.dict(os.environ,self.env,clear=True);environment.start();self.addCleanup(environment.stop)
        normal=patch.object(self.project,'normal_user',return_value=True);normal.start();self.addCleanup(normal.stop)

    def git(self, *arguments):
        return subprocess.run(['git',*arguments],env=self.env,check=True,capture_output=True,text=True).stdout.strip()

    def repository(self):
        repo=self.root/'original repo';self.git('init','-q',str(repo))
        (repo/'student.txt').write_text('committed bytes\n')
        self.git('-C',str(repo),'add','student.txt')
        self.git('-C',str(repo),'-c','user.name=Synthetic Student','-c','user.email=student@example.invalid','-c','commit.gpgsign=false','commit','-qm','fixture')
        return repo

    def snapshot(self):
        return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_real_repository_and_fork_configuration_are_preserved(self):
        repo=self.repository();self.git('-C',str(repo),'remote','add','origin','https://example.invalid/student/fork.git')
        (repo/'student.txt').write_text('uncommitted work\n');before=self.snapshot()
        value=self.project.inspect(str(repo))
        self.assertEqual(value,dict(schema=1,status='verified',reason='verified',root=str(repo)))
        self.assertEqual(self.snapshot(),before)

    def test_linked_worktree_git_file_is_verified_without_touching_either_tree(self):
        repo=self.repository();worktree=self.root/'moved worktree'
        self.git('-C',str(repo),'worktree','add','-qb','student-worktree',str(worktree))
        self.assertTrue((worktree/'.git').is_file())
        (worktree/'student.txt').write_text('dirty worktree\n');before=self.snapshot()
        self.assertEqual(self.project.inspect(str(worktree))['status'],'verified')
        self.assertEqual(self.snapshot(),before)

    def test_fake_git_entries_do_not_prove_a_working_folder(self):
        for entry in ('directory','file'):
            folder=self.root/entry;folder.mkdir()
            if entry=='directory':(folder/'.git').mkdir()
            else:(folder/'.git').write_text('gitdir: /missing/sde-project-fixture\n')
            value=self.project.inspect(str(folder))
            self.assertEqual(value['status'],'incomplete');self.assertIsNone(value['root'])

    def test_a_parent_repository_cannot_certify_the_selected_child(self):
        repo=self.repository();child=repo/'ordinary subfolder';child.mkdir()
        self.assertEqual(self.project.inspect(str(child))['reason'],'rootMismatch')

    def test_git_environment_cannot_select_another_repository_or_write_trace_files(self):
        repo=self.repository();other=self.root/'not a repository';other.mkdir();trace=self.root/'trace'
        with patch.dict(os.environ,{'GIT_DIR':str(repo/'.git'),'GIT_WORK_TREE':str(repo),'GIT_TRACE':str(trace),'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'safe.directory','GIT_CONFIG_VALUE_0':'*'}):
            self.assertEqual(self.project.inspect(str(other))['status'],'incomplete')
            self.assertEqual(self.project.inspect(str(repo))['status'],'verified')
            self.assertEqual(os.environ['GIT_DIR'],str(repo/'.git'))
            self.assertFalse(trace.exists())

    def test_repository_hooks_and_fsmonitor_are_not_executed(self):
        repo=self.repository();hooks=self.root/'hooks';hooks.mkdir();marker=self.root/'hook-ran'
        hook=hooks/'post-checkout';hook.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\n');hook.chmod(0o755)
        self.git('-C',str(repo),'config','core.hooksPath',str(hooks))
        self.git('-C',str(repo),'config','core.fsmonitor',str(hook));before=self.snapshot()
        self.assertEqual(self.project.inspect(str(repo))['status'],'verified')
        self.assertFalse(marker.exists());self.assertEqual(self.snapshot(),before)

    def test_elevation_invalid_paths_and_unavailable_locations_never_run_git(self):
        from unittest.mock import Mock
        run=Mock()
        with patch.object(self.project,'normal_user',return_value=False):
            self.assertEqual(self.project.inspect(str(self.root),run)['reason'],'normalUserRequired')
        for path in ('relative',str(self.root)+'|data',str(self.root)+'\n',str(self.root)+'\u202e'):
            self.assertEqual(self.project.inspect(path,run)['reason'],'unsupportedPath')
        self.assertEqual(self.project.inspect(str(self.root/'missing'),run)['reason'],'locationUnavailable')
        file=self.root/'file';file.write_text('not a directory')
        self.assertEqual(self.project.inspect(str(file),run)['reason'],'notDirectory')
        run.assert_not_called()

    def test_trust_refusal_timeout_and_malformed_output_remain_incomplete(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        for code,text in [(1,'fatal: dubious ownership'),(-1,''),(0,str(self.root)),(0,str(self.root)+'\nfalse'),(0,str(self.root)+'\ntrue\nextra')]:
            run=Mock(return_value=SimpleNamespace(code=code,text=text))
            value=self.project.inspect(str(self.root),run)
            self.assertEqual(value['status'],'incomplete');self.assertIsNone(value['root'])
            self.assertEqual(run.call_args.args[1],6)
            self.assertIn('--no-optional-locks',run.call_args.args[0])
            self.assertIn('--no-pager',run.call_args.args[0])
            self.assertIn('core.fsmonitor=false',run.call_args.args[0])
            self.assertNotIn('safe.directory=*',run.call_args.args[0])

    def test_missing_git_is_incomplete_rather_than_a_missing_project(self):
        with patch.object(self.project.shutil,'which',return_value=None):
            self.assertEqual(self.project.inspect(str(self.root))['reason'],'gitUnavailable')

    def test_validation_requires_one_verified_result_and_rejects_injected_names(self):
        import io
        from contextlib import redirect_stdout
        for name,passed in [('student-project',True),('student-project',False),('bad\nproject',True)]:
            with patch.object(self.project,'inspect',return_value={'status':'verified' if passed else 'incomplete'}),redirect_stdout(io.StringIO()) as output:
                code=self.project.validate(name,str(self.root))
            lines=output.getvalue().splitlines()
            self.assertEqual(len(lines),1)
            self.assertEqual(code,0 if passed and name=='student-project' else 1)
            self.assertTrue(lines[0].startswith('SKYVIEW_EVENT|validation|'+('PASS' if code==0 else 'FAIL')+'|'))


if __name__ == "__main__":
    unittest.main()
