import unittest
from pathlib import Path

import yaml

from ci_timings import summarize


class Timings(unittest.TestCase):
    def test_caching_keeps_original_jobs_and_full_native_regression(self):
        root = Path(__file__).resolve().parents[1]
        jobs = yaml.safe_load((root / '.github/workflows/build-dev-setup.yml').read_text())['jobs']
        self.assertEqual(set(jobs), {'scope', 'checks', 'native', 'update-trust', 'release'})
        self.assertEqual(jobs['checks']['needs'], 'scope')
        self.assertEqual(jobs['release']['needs'], ['checks', 'native', 'update-trust'])
        native_test = next(s for s in jobs['native']['steps'] if s.get('name') == 'Rust tests')
        self.assertEqual(native_test['run'], 'cargo test --locked -- --nocapture')
        for name in ('native', 'update-trust'):
            cache = next(s for s in jobs[name]['steps'] if s.get('uses') == 'Swatinem/rust-cache@v2')
            self.assertIn('coordination -> target', cache['with']['workspaces'].splitlines())
            self.assertIn('updater -> target', cache['with']['workspaces'].splitlines())

    def job(self, name, start, end, conclusion='success'):
        return dict(name=name, started_at=f'2026-11-01T00:00:{start:02d}Z',
                    completed_at=f'2026-11-01T00:00:{end:02d}Z' if end else None,
                    conclusion=conclusion, steps=[])

    def test_overlapping_jobs_count_once_for_elapsed_but_twice_for_runner_time(self):
        result = summarize([self.job('native', 1, 20), self.job('migration', 5, 25),
                            self.job('release', 25, 25, 'skipped')])
        self.assertEqual(result['observed_job_span_seconds'], 24)
        self.assertEqual(result['completed_runner_seconds'], 39)
        self.assertTrue(result['all_jobs_successful'])

    def test_pending_failed_and_empty_results_cannot_be_reported_as_success(self):
        for jobs in ([], [self.job('migration', 1, None, None)],
                     [self.job('native', 1, 20), self.job('migration', 5, 25, 'failure')]):
            self.assertFalse(summarize(jobs)['all_jobs_successful'])

    def test_step_timings_preserved(self):
        job = self.job('native', 1, 25)
        job['steps'] = [dict(name='Rust tests', started_at=job['started_at'],
                             completed_at=job['completed_at'], conclusion='success')]
        self.assertEqual(summarize([job])['jobs'][0]['steps'][0]['seconds'], 24)
