"""Check the real frontend -> handler -> generated permission -> capability wiring."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CommandPermissions(unittest.TestCase):
    def test_frontend_commands_are_registered_and_granted_to_main(self):
        source = ROOT / 'installer/src'
        invoked = set()
        for path in source.glob('*.ts*'):
            if '.test.' not in path.name:
                invoked.update(re.findall(r'\binvoke(?:<[^>]+>)?\(\s*["\'](\w+)["\']', path.read_text(encoding='utf-8')))
        rust = (ROOT / 'installer/src-tauri/src/main.rs').read_text(encoding='utf-8')
        registered = set(re.findall(r'\b(?:\w+::)?(\w+)\s*,?', re.search(r'generate_handler!\[(.*?)\]', rust, re.S)[1]))
        build = (ROOT / 'installer/src-tauri/build.rs').read_text(encoding='utf-8')
        generated = set(re.findall(r'"(\w+)"', re.search(r'\.commands\(&\[(.*?)\]\)', build, re.S)[1]))
        cap = json.loads((ROOT / 'installer/src-tauri/capabilities/main.json').read_text(encoding='utf-8'))
        granted = {p.removeprefix('allow-').replace('-', '_') for p in cap['permissions'] if p.startswith('allow-')}
        self.assertTrue(invoked, 'No frontend commands parsed')
        self.assertFalse(invoked - registered, f'Frontend commands lack handlers: {invoked - registered}')
        self.assertFalse(registered - generated, f'Handlers lack generated permissions: {registered - generated}')
        self.assertFalse(invoked - granted, f'Frontend commands denied to main window: {invoked - granted}')
        self.assertEqual(generated, registered, 'Generated app permissions and registered handlers drifted')
        self.assertEqual(granted, registered, 'Main window app command grants and handlers drifted')
        self.assertEqual(cap['windows'], ['main'])
        self.assertNotIn('remote', cap, 'Local command permissions must not grant remote origins')
        self.assertEqual(cap['permissions'].count('allow-set-self-update-paused'), 1)

    def test_privileged_helper_has_no_uncoordinated_script_launch(self):
        source = (ROOT / 'installer/src-tauri/src/process.rs').read_text()
        helper = source.split('pub fn helper(', 1)[1].split('pub fn elevated(', 1)[0]
        self.assertEqual(helper.count('coordinated_stream(cmd,'), 2)
        self.assertFalse(re.search(r'\bstream\(cmd,', helper))
        self.assertEqual(helper.count('preflight::before_privileged_operation('), 2)
        self.assertIn('if cfg!(debug_assertions)', helper)
        self.assertIn('resource_backend()?', helper)

    def test_helper_coordination_is_backend_authority_not_frontend_uncertainty(self):
        source = (ROOT / 'installer/src-tauri/src/process.rs').read_text()
        adapter = source.split('fn coordinated_stream(', 1)[1].split('#[cfg(test)]', 1)[0]
        self.assertNotIn('acknowledged_uncertainty', adapter)
        self.assertLess(adapter.index('mutation::begin('), adapter.index('.run_supervised('))
        self.assertLess(adapter.index('inspection::collect()'), adapter.index('guard.finish_known()'))
        preflight = (ROOT / 'installer/src-tauri/src/preflight.rs').read_text()
        self.assertIn('inspect_with_coordination(root, operation, true)', preflight)
        self.assertIn('before_operation_with(root, operation, acknowledged_uncertainty, emit, false)', preflight)


if __name__ == '__main__':
    unittest.main()
