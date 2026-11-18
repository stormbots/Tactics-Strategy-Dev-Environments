"""Schedule regressions; package managers and development tools never run."""
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, REPO / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


schedule = load('schedule', 'linux/lib/schedule.py')
hook = load('history', 'linux/self-update/history.py')
INVOCATION = 'a' * 32


def receipt(result='success', end='2026-10-12T22:18:56+00:00'):
    return dict(schemaVersion=1, invocation=INVOCATION,
                startedAt='2026-10-12T22:18:48+00:00', completedAt=end,
                lastResult=result)


class ScheduleHistory(unittest.TestCase):
    def inspect(self, history, **service):
        timer = dict(LoadState='loaded', UnitFileState='enabled', ActiveState='active',
                     TimersCalendar='{ OnCalendar=Sun *-*-* 03:00:00 ; next_elapse=x }',
                     RandomizedDelayUSec='1h', Persistent='yes',
                     LastTriggerUSec='Sun 2026-10-11 14:26:00 UTC')
        unit = dict(LoadState='loaded', ActiveState='inactive', Result='success',
                    ExecMainStatus='0', ExecMainStartTimestamp='', InvocationID='')
        unit.update(service)
        with patch.object(schedule, 'show', side_effect=[timer, unit]), \
                patch.object(schedule, 'read_history', return_value=history):
            return schedule.inspect()

    def test_latest_success_survives_missing_systemd_timestamps(self):
        observed = self.inspect(receipt())
        self.assertEqual(observed['lastResult'], 'success')
        self.assertEqual(observed['lastRun'], receipt()['startedAt'])
        self.assertEqual(observed['status'], 'enabled')
        self.assertTrue(observed['catchUp'])

    def test_new_launcher_failure_replaces_old_tool_success(self):
        self.assertEqual(self.inspect(receipt('failure'))['lastResult'], 'failure')

    def test_interrupted_start_does_not_reuse_old_success(self):
        observed = self.inspect(receipt('unavailable', None))
        self.assertEqual(observed['lastResult'], 'unavailable')
        self.assertIn('interrupted', observed['resultDetail'])

    def test_running_service_takes_priority_over_completed_history(self):
        self.assertEqual(self.inspect(receipt(), ActiveState='activating')['lastResult'], 'running')

    def test_newer_failed_or_unrecorded_invocation_cannot_claim_old_success(self):
        for changes in (dict(InvocationID='b' * 32), dict(Result='exit-code'),
                        dict(ExecMainStartTimestamp='Mon 2026-10-12 22:20:00 UTC', Result='exit-code', ExecMainStatus='1')):
            with self.subTest(changes=changes):
                self.assertNotEqual(self.inspect(receipt(), **changes)['lastResult'], 'success')
        timer = {'LastTriggerUSec': 'Mon 2026-10-12 22:20:00 UTC'}
        self.assertIsNone(schedule.durable_result(receipt(), {}, timer))

    def test_missing_history_stays_unavailable_without_restart_claim(self):
        observed = self.inspect(None)
        self.assertEqual(observed['lastResult'], 'unavailable')
        self.assertNotIn('restart', observed['resultDetail'])

    def test_native_service_result_still_works_without_durable_record(self):
        observed = self.inspect(None, ExecMainStartTimestamp='Mon 2026-10-12 22:18:48 UTC')
        self.assertEqual(observed['lastResult'], 'success')

    def test_invalid_history_is_rejected(self):
        for changes in (dict(schemaVersion=True), dict(invocation='../bad'),
                        dict(lastResult='current'), dict(completedAt=None),
                        dict(completedAt='2026-10-11T00:00:00+00:00'),
                        dict(startedAt='2026-10-12T22:18:48')):
            with self.subTest(changes=changes), self.assertRaises((ValueError, TypeError)):
                schedule.validate_history({**receipt(), **changes})

    def test_hooks_clear_history_at_start_and_record_systemd_failure(self):
        with patch.object(hook, 'publish') as publish:
            hook.record_attempt('start', {'INVOCATION_ID': INVOCATION})
            self.assertEqual(publish.call_args.args[0]['lastResult'], 'unavailable')
            self.assertIsNone(publish.call_args.args[0]['completedAt'])
        for environment, expected in (
                ({'SERVICE_RESULT': 'success', 'EXIT_CODE': 'exited', 'EXIT_STATUS': '0'}, 'success'),
                ({'SERVICE_RESULT': 'exit-code', 'EXIT_CODE': 'exited', 'EXIT_STATUS': '1'}, 'failure'),
                ({'SERVICE_RESULT': 'signal', 'EXIT_CODE': 'killed', 'EXIT_STATUS': 'TERM'}, 'failure'),
                ({'SERVICE_RESULT': 'exit-code', 'EXIT_CODE': 'exited', 'EXIT_STATUS': '75'}, 'deferred'),
                ({'SERVICE_RESULT': 'success'}, 'unavailable')):
            with self.subTest(environment=environment), \
                    patch.object(hook, 'publish') as publish, \
                    patch.object(hook, 'trusted', side_effect=OSError):
                hook.record_attempt('finish', {'INVOCATION_ID': INVOCATION, **environment})
                self.assertEqual(publish.call_args.args[0]['lastResult'], expected)


class ScheduleValidation(unittest.TestCase):
    def test_shell_fallback_retains_real_tool_failures_and_warns_only_about_inspection(self):
        source = (REPO / 'linux/Validate-SkyviewStudentDev.sh').read_text()
        fragment = source[source.index('SCHEDULE_HELPER='):source.index('PYCHARM_LOCATION=')]
        with tempfile.TemporaryDirectory(prefix='sde schedule ') as directory:
            lib = Path(directory) / 'lib'
            lib.mkdir()
            (lib / 'schedule.py').write_text('raise SystemExit(1)\n')
            program = ('PASS_COUNT=2; WARN_COUNT=1; FAIL_COUNT=1\n'
                       'info() { printf "SKYVIEW_EVENT|validation|INFO|%s\\n" "$*"; }\n' + fragment +
                       '\nprintf "COUNTS %s %s %s\\n" "$PASS_COUNT" "$WARN_COUNT" "$FAIL_COUNT"')
            result = subprocess.run(['/bin/bash', '-c', program], text=True,
                                    capture_output=True, timeout=5,
                                    env={**os.environ, 'SCRIPT_DIR': directory, 'SKYVIEW_LIB': str(lib)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SKYVIEW_EVENT|validation|INFO|Weekly maintenance could not be checked.', result.stdout)
        self.assertIn('COUNTS 2 1 1', result.stdout)

    def test_schedule_states_are_information_and_keep_their_actual_meaning(self):
        for status, active, expected in (
                ('enabled', True, 'timer is enabled. View Schedule'),
                ('enabled', False, 'enabled but inactive'),
                ('disabled', False, 'Future automatic development-tool maintenance is not scheduled'),
                ('disabled', True, 'may still run in this session'),
                ('missing', False, 'timer is missing'),
                ('unavailable', False, 'could not be checked')):
            for history in ('success', 'failure', 'deferred', 'running', 'unavailable'):
                record = dict(status=status, active=active, lastResult=history)
                before = dict(record)
                with self.subTest(status=status, active=active, history=history), \
                        patch.object(schedule, 'inspect', return_value=record), \
                        contextlib.redirect_stdout(io.StringIO()) as output:
                    schedule.main(['--validation'])
                    line = output.getvalue().strip()
                    self.assertTrue(line.startswith('SKYVIEW_EVENT|validation|INFO|'))
                    self.assertIn(expected, line)
                    self.assertNotIn('Repair', line)
                    self.assertEqual(record, before)

    def test_json_inspection_contract_is_unchanged_and_other_options_are_rejected(self):
        record = dict(status='disabled', active=False, lastResult='failure')
        with patch.object(schedule, 'inspect', return_value=record), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            schedule.main([])
        self.assertEqual(json.loads(output.getvalue()), record)
        with patch.object(schedule, 'inspect') as inspect, self.assertRaises(SystemExit):
            schedule.main(['--enable'])
        inspect.assert_not_called()


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0,
                     'Protected filesystem checks require disposable Linux root runner')
class ProtectedHistory(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory(prefix='sde-history-test-', dir='/var/lib')
        self.root = Path(self.fixture.name)
        self.root.chmod(0o755)
        self.path = self.root / 'maintenance-history.json'
        self.patches = [patch.object(hook, 'ROOT', self.root),
                        patch.object(hook, 'HISTORY', self.path),
                        patch.object(schedule, 'HISTORY', self.path)]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.fixture.cleanup()

    def test_atomic_publication_is_readable_and_retains_start_identity(self):
        hook.record_attempt('start', {'INVOCATION_ID': INVOCATION})
        start = schedule.read_history()['startedAt']
        hook.record_attempt('finish', dict(INVOCATION_ID=INVOCATION,
                            SERVICE_RESULT='success', EXIT_CODE='exited', EXIT_STATUS='0'))
        self.assertEqual(schedule.read_history()['startedAt'], start)
        self.assertEqual(schedule.read_history()['lastResult'], 'success')
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o644)

    def test_untrusted_or_malformed_history_never_claims_success(self):
        hook.publish(receipt())
        self.path.chmod(0o666)
        self.assertIsNone(schedule.read_history())
        self.path.chmod(0o644)
        self.path.write_text('x' * 4097)
        self.assertIsNone(schedule.read_history())
        self.path.write_text('{')
        self.assertIsNone(schedule.read_history())

    def test_links_and_writable_ancestors_are_rejected(self):
        target = self.root / 'target'
        target.write_text(json.dumps(receipt()))
        self.path.symlink_to(target)
        self.assertIsNone(schedule.read_history())
        self.path.unlink()
        os.link(target, self.path)
        self.assertIsNone(schedule.read_history())
        self.path.unlink()
        hook.publish(receipt())
        self.root.chmod(0o777)
        self.assertIsNone(schedule.read_history())
        self.root.chmod(0o755)

    def test_real_systemd_hooks_record_success_and_later_launcher_failure(self):
        if os.environ.get('SDE_REQUIRE_SCHEDULE_SYSTEMD') != '1':
            self.skipTest('Real systemd integration is enabled on disposable CI only')
        self.assertTrue(Path('/run/systemd/system').is_dir(), 'Booted systemd runner required')
        driver = self.root / 'driver.py'
        driver.write_text(
            'import importlib.util,sys\nfrom pathlib import Path\n'
            f's=importlib.util.spec_from_file_location("history", {str(REPO / "linux/self-update/history.py")!r})\n'
            'h=importlib.util.module_from_spec(s);s.loader.exec_module(h)\n'
            f'h.ROOT=Path({str(self.root)!r});h.HISTORY=h.ROOT/"maintenance-history.json"\n'
            'h.main()\n')
        unit = Path('/run/systemd/system') / (self.root.name + '.service')
        try:
            for executable, expected in (('/usr/bin/true', 'success'), ('/usr/bin/false', 'failure')):
                unit.write_text('[Service]\nType=oneshot\n'
                                f'ExecStartPre=/usr/bin/python3 -I {driver} start\n'
                                f'ExecStart={executable}\n'
                                f'ExecStopPost=/usr/bin/python3 -I {driver} finish\n')
                subprocess.run(['systemctl', 'daemon-reload'], check=True, timeout=30)
                subprocess.run(['systemctl', 'reset-failed', unit.name], check=False, timeout=10)
                result = subprocess.run(['systemctl', 'start', unit.name], check=False, timeout=30)
                self.assertEqual(result.returncode == 0, expected == 'success')
                self.assertEqual(schedule.read_history()['lastResult'], expected)
        finally:
            subprocess.run(['systemctl', 'stop', unit.name], check=False, timeout=30)
            subprocess.run(['systemctl', 'reset-failed', unit.name], check=False, timeout=10)
            unit.unlink(missing_ok=True)
            subprocess.run(['systemctl', 'daemon-reload'], check=True, timeout=30)

    def test_real_timer_disabled_and_inactive_states_remain_read_only_information(self):
        if os.environ.get('SDE_REQUIRE_SCHEDULE_SYSTEMD') != '1':
            self.skipTest('Real systemd integration is enabled on disposable CI only')
        self.assertTrue(Path('/run/systemd/system').is_dir(), 'Booted systemd runner required')
        name = 'skyview-ci-schedule-' + self.root.name
        timer = Path('/run/systemd/system') / (name + '.timer')
        service = timer.with_suffix('.service')
        def systemctl(*args):
            subprocess.run(['systemctl', *args], check=True, capture_output=True, timeout=30)
        try:
            # This harmless fixture cannot fire during CI and uses no real
            # maintenance task, package manager, project or user preference.
            service.write_text('[Service]\nType=oneshot\nExecStart=/usr/bin/true\n')
            timer.write_text('[Timer]\nOnCalendar=2099-01-01 00:00:00 UTC\n'
                             '[Install]\nWantedBy=timers.target\n')
            systemctl('daemon-reload')
            systemctl('enable', '--runtime', timer.name)
            with patch.object(schedule, 'TIMER', timer.name), patch.object(schedule, 'SERVICE', service.name):
                for action, status, active, text in (
                        (None, 'enabled', False, 'enabled but inactive'),
                        ('start', 'enabled', True, 'timer is enabled'),
                        ('disable', 'disabled', True, 'may still run in this session'),
                        ('stop', 'disabled', False, 'not scheduled')):
                    if action == 'disable':
                        systemctl('disable', '--runtime', timer.name)
                    elif action:
                        systemctl(action, timer.name)
                    before = schedule.show(timer.name)
                    with contextlib.redirect_stdout(io.StringIO()) as output:
                        schedule.main(['--validation'])
                    self.assertTrue(output.getvalue().startswith('SKYVIEW_EVENT|validation|INFO|'))
                    self.assertIn(text, output.getvalue())
                    record = schedule.inspect()
                    self.assertEqual((record['status'], record['active']), (status, active))
                    after = schedule.show(timer.name)
                    for key in ('UnitFileState', 'ActiveState', 'LastTriggerUSec'):
                        self.assertEqual(after.get(key), before.get(key))
        finally:
            subprocess.run(['systemctl', 'stop', timer.name], check=False, capture_output=True, timeout=30)
            subprocess.run(['systemctl', 'disable', '--runtime', timer.name], check=False, capture_output=True, timeout=30)
            timer.unlink(missing_ok=True)
            service.unlink(missing_ok=True)
            systemctl('daemon-reload')


if __name__ == '__main__':
    unittest.main()
