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


if __name__ == '__main__':
    unittest.main()
