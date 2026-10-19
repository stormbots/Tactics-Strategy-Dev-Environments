from pathlib import Path
import tempfile
import unittest
from report_ci_failure import annotation


class FailureReport(unittest.TestCase):
    def test_bounded_tail_and_command_escaping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'failure.txt'
            path.write_bytes(b'not retained' + b'x' * 9000 + b'failure%\r\n::warning::text')
            result = annotation(path)
            self.assertNotIn('not retained', result)
            self.assertTrue(result.endswith('failure%25%0D%0A::warning::text'))
            self.assertNotIn('\n', result)
            self.assertLess(len(result), 8300)
