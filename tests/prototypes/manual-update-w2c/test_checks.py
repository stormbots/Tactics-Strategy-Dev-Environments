"""Focused W2c fixture checks, not production journal/parser acceptance."""
import json
from pathlib import Path
import tempfile
import unittest

from run_experiment import inspect_intent, publish_intent, expected_fixture


class FixtureChecks(unittest.TestCase):
    def test_only_absence_has_no_intent(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            self.assertEqual(inspect_intent(Path(root)), dict(present=False, reason='absent'))

    def test_published_fixture_remains_unresolved_on_repeated_inspection(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            path = Path(root)
            published = publish_intent(path)
            self.assertEqual(published['operations'], ['exclusive_create_temporary_0600',
                'write_complete', 'fsync_temporary_file', 'replace_into_intent_name', 'fsync_parent_directory'])
            self.assertEqual(published['observed']['reason'], 'unresolved_fixture')
            self.assertEqual(inspect_intent(path), published['observed'])
            self.assertEqual(inspect_intent(path), published['observed'])
            with self.assertRaisesRegex(RuntimeError, 'already exists'):
                publish_intent(path)

    def test_malformed_unknown_boolean_and_oversized_fixtures_block(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            path = Path(root)
            for raw in (b'{', b'x' * 4097,
                        json.dumps({**expected_fixture(path), 'schema': 2}).encode(),
                        json.dumps({**expected_fixture(path), 'schema': True}).encode(),
                        json.dumps({**expected_fixture(path), 'extra': 'ignored?'}).encode()):
                with self.subTest(raw=raw[:30]):
                    (path / 'intent.json').write_bytes(raw)
                    self.assertTrue(inspect_intent(path)['present'])
                    self.assertEqual(inspect_intent(path)['reason'], 'invalid_or_unreadable_fixture')

    def test_duplicate_fields_block(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            path = Path(root)
            raw = json.dumps(expected_fixture(path))
            (path / 'intent.json').write_text(raw[:-1] + ', "state": "unresolved"}')
            self.assertEqual(inspect_intent(path)['reason'], 'invalid_or_unreadable_fixture')

    def test_dangling_symlink_is_not_absence(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            path = Path(root)
            (path / 'intent.json').symlink_to('missing-fixture')
            self.assertTrue(inspect_intent(path)['present'])
            self.assertEqual(inspect_intent(path)['reason'], 'invalid_or_unreadable_fixture')


if __name__ == '__main__':
    unittest.main()
