import copy
import unittest
from unittest.mock import Mock

from verify_native_ci import REQUIRED, completed_native_steps, require_native_validation


class NativeEvidence(unittest.TestCase):
    def setUp(self):
        self.jobs = {'total_count': 2, 'jobs': [
            {'conclusion': 'success', 'steps': [{'name': name, 'conclusion': 'success'}]}
            for name in sorted(REQUIRED)]}
        self.run = {'id': 42, 'head_sha': 'expected', 'head_branch': 'main',
                    'event': 'workflow_dispatch', 'conclusion': 'success'}

    def test_actual_both_platform_completion_passes(self):
        require_native_validation({'workflow_runs': [self.run]}, 'expected', lambda _: self.jobs)

    def test_skipped_failed_missing_or_truncated_evidence_rejected(self):
        for outcome in ['skipped', 'failure', 'cancelled', None]:
            jobs = copy.deepcopy(self.jobs)
            jobs['jobs'][0]['steps'][0]['conclusion'] = outcome
            self.assertFalse(completed_native_steps(jobs))
        jobs = copy.deepcopy(self.jobs)
        jobs['jobs'][0]['conclusion'] = 'failure'
        self.assertFalse(completed_native_steps(jobs))
        self.assertFalse(completed_native_steps({'total_count': 3, 'jobs': self.jobs['jobs']}))
        self.assertFalse(completed_native_steps({'total_count': 0, 'jobs': []}))
        self.assertFalse(completed_native_steps({}))

    def test_other_commit_branch_event_or_failed_run_is_not_native_proof(self):
        for key, value in [('head_sha', 'other'), ('head_branch', 'release/v1.2.uat'),
                           ('event', 'push'), ('event', 'pull_request'),
                           ('conclusion', 'failure'), ('id', '42')]:
            run = {**self.run, key: value}
            fetch = Mock(return_value=self.jobs)
            with self.assertRaises(RuntimeError):
                require_native_validation({'workflow_runs': [run]}, 'expected', fetch)
            fetch.assert_not_called()

    def test_green_packaging_only_run_does_not_count(self):
        jobs = copy.deepcopy(self.jobs)
        for job in jobs['jobs']:
            job['steps'][0]['conclusion'] = 'skipped'
        with self.assertRaises(RuntimeError):
            require_native_validation({'workflow_runs': [self.run]}, 'expected', lambda _: jobs)


if __name__ == '__main__':
    unittest.main()
