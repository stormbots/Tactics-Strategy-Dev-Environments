"""Metadata fixtures: never provision the host."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "linux/lib" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
tools = module("tool_records")
schedule = module("schedule")

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

if __name__ == "__main__":
    unittest.main()
