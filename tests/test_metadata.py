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
        self.assertEqual(records["Firefox"]["updateCheck"], "unavailable")
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

    def test_failed_extension_listing_cannot_supply_partial_required_pass(self):
        if os.name != 'posix':
            return
        commands = self.root / 'bin'
        commands.mkdir()
        cli = commands / 'codium'
        cli.write_text('#!/bin/sh\necho required.extension\nexit 7\n')
        cli.chmod(0o700)
        policy = self.root / 'extensions.txt'
        policy.write_text('required.extension\n')
        source = (ROOT / 'linux/Validate-SkyviewStudentDev.sh').read_text()
        fragment = source[source.index('EXT_FILE='):source.index('\nif systemctl')]
        program = 'FAIL_COUNT=0; PASS_COUNT=0\nfail() { FAIL_COUNT=$((FAIL_COUNT+1)); }; pass() { PASS_COUNT=$((PASS_COUNT+1)); }\n' + fragment + '\nprintf "COUNTS %s %s\\n" "$PASS_COUNT" "$FAIL_COUNT"'
        result = subprocess.run(['/bin/bash', '-c', program], env={**os.environ, 'PATH': str(commands) + os.pathsep + os.environ['PATH'],
                                'SKYVIEW_SHARE': str(self.root), 'SCRIPT_DIR': str(self.root), 'TARGET_USER': '', 'TARGET_HOME': str(self.root)},
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('COUNTS 0 1', result.stdout)

    def test_version_command_must_succeed_with_a_real_version(self):
        if os.name != 'posix':
            return
        commands = self.root / 'bin'
        commands.mkdir()
        cli = commands / 'codium'
        source = (ROOT / 'linux/Validate-SkyviewStudentDev.sh').read_text()
        start = source.index('check_command() {')
        fragment = source[start:source.index('\nprintf', start)]
        program = 'FAIL_COUNT=0; PASS_COUNT=0\nfail() { FAIL_COUNT=$((FAIL_COUNT+1)); }; pass() { PASS_COUNT=$((PASS_COUNT+1)); }\n' + fragment + '\ncheck_command codium VSCodium\nprintf "COUNTS %s %s\\n" "$PASS_COUNT" "$FAIL_COUNT"'
        for code, version, counts in ((7, '1.90.0', '0 1'), (0, 'not a version', '0 1'), (0, '1.90.0', '1 0')):
            cli.write_text(f'#!/bin/sh\necho "{version}"\nexit {code}\n')
            cli.chmod(0o700)
            result = subprocess.run(['/bin/bash', '-c', program], env={**os.environ, 'PATH': str(commands) + os.pathsep + os.environ['PATH']},
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('COUNTS ' + counts, result.stdout)


if __name__ == "__main__":
    unittest.main()
