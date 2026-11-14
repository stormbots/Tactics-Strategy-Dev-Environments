"""Reference validation must catch broken docs without executing their examples."""
import os
from pathlib import Path
import tempfile
import unittest

from check_docs import validate


class ReferenceChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        return target

    def test_new_guide_reference_links_anchors_html_images_and_encoded_spaces(self):
        self.write('docs/chapter one.md', '# First chapter\n\n<a id="custom"></a>\n')
        self.write('README.md', '# Project\n\n[Read][chapter]\n\n[chapter]: docs/chapter%20one.md#first-chapter\n\n<a href="docs/chapter%20one.md#custom">Read</a>\n')
        self.assertEqual(validate(self.root, ['README.md', 'docs/chapter one.md']), [])

    def test_duplicate_headings_keep_distinct_local_anchors(self):
        self.write('docs/target.md', '# Heading\n\n# Heading\n\n# Heading-1\n')
        self.write('docs/index.md', '# Index\n\n[A](target.md#heading) [B](target.md#heading-1) [C](target.md#heading-1-1)\n')
        self.assertEqual(validate(self.root, ['docs/index.md', 'docs/target.md']), [])

    def test_broken_target_and_markdown_anchor_fail(self):
        self.write('docs/target.md', '# Existing\n')
        for link in ('missing.md', 'target.md#missing'):
            with self.subTest(link=link):
                self.write('docs/guide.md', '# Guide\n\n[Read](' + link + ')\n')
                self.assertTrue(validate(self.root, ['docs/guide.md']))

    def test_deleting_a_reference_checks_unchanged_inbound_links(self):
        self.write('README.md', '# Index\n\n[Read](docs/removed.md)\n')
        errors = validate(self.root, ['docs/removed.md'], ['README.md'])
        self.assertTrue(any('missing local target' in error for error in errors))
        self.assertEqual(validate(self.root, ['docs/removed.md']), [])

    def test_unrelated_historical_link_debt_does_not_block_a_new_guide(self):
        self.write('docs/old.md', '# Old\n\n[Old missing link](historical.md)\n')
        self.write('docs/new.md', '# New\n')
        self.assertEqual(validate(self.root, ['docs/new.md'], ['docs/old.md']), [])

    def test_empty_unclosed_fence_nul_invalid_encoding_and_missing_newline_fail(self):
        for contents in ('', '# Guide\n```bash\necho hello\n', '# Guide\x00\n', '# Guide'):
            with self.subTest(contents=contents):
                self.write('docs/guide.md', contents)
                self.assertTrue(validate(self.root, ['docs/guide.md']))
        (self.root / 'docs/guide.md').write_bytes(b'\xff\xfe')
        self.assertTrue(validate(self.root, ['docs/guide.md']))

    def test_example_commands_and_example_links_are_never_executed_or_followed(self):
        self.write('docs/guide.md', '# Guide\n\n```bash\ntouch owned\n[example](missing.md)\n```\n\n`[example](also-missing.md)`\n')
        self.assertEqual(validate(self.root, ['docs/guide.md']), [])
        self.assertFalse((self.root / 'owned').exists())

    def test_external_authenticated_urls_are_not_fetched(self):
        self.write('docs/guide.md', '# Guide\n\n[Private](https://invalid.example/private)\n[Email](mailto:student@example.com)\n')
        self.assertEqual(validate(self.root, ['docs/guide.md']), [])

    def test_reference_manifest_cannot_escape_approved_locations(self):
        self.write('outside.md', '# Outside\n')
        for path in ('../outside.md', 'docs/../outside.md', '/outside.md', 'docs/tool.py'):
            self.assertTrue(validate(self.root, [path]))
        self.write('docs/guide.md', '# Guide\n\n[Outside](../../outside.md)\n')
        self.assertTrue(validate(self.root, ['docs/guide.md']))

    @unittest.skipUnless(os.name == 'posix', 'POSIX executable and symlink fixture')
    def test_executable_or_symlink_references_cannot_pass(self):
        target = self.write('docs/code.md', '# Executable\n')
        target.chmod(0o755)
        self.assertTrue(validate(self.root, ['docs/code.md']))
        link = self.root / 'docs/link.md'; link.symlink_to(target)
        self.assertTrue(validate(self.root, ['docs/link.md']))

    def test_image_structure_and_inbound_references(self):
        target = self.write('docs/diagram.svg', '<svg xmlns="http://www.w3.org/2000/svg"><rect width="5" height="5"/></svg>\n')
        self.write('docs/guide.md', '# Guide\n\n![Diagram](diagram.svg)\n')
        self.assertEqual(validate(self.root, ['docs/guide.md', 'docs/diagram.svg']), [])
        target.write_text('<not-svg/>')
        self.assertTrue(validate(self.root, ['docs/diagram.svg']))
        target.unlink()
        self.assertTrue(validate(self.root, ['docs/diagram.svg'], ['docs/guide.md']))


if __name__ == '__main__':
    unittest.main()
