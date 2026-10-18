"""Static/pure policy checks only: never open KVM or execute inventory code."""
import ast
from pathlib import Path
import unittest
import yaml
from ci_scope import MINT_INFRA_PATHS, application_required

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return yaml.load((ROOT/'.github/workflows'/name).read_text(), Loader=yaml.BaseLoader)


def allowed(job, *, event='workflow_dispatch', repo='stormbots/Tactics-Strategy-Dev-Environments',
            ref='refs/heads/main', workflow_ref='stormbots/Tactics-Strategy-Dev-Environments/.github/workflows/mint-host-inventory.yml@refs/heads/main',
            enabled='', ready='', sha='a'*40, approved=''):
    expression = job['if']
    values = {'github.event_name': event, 'github.repository': repo, 'github.ref': ref,
              'github.workflow_ref': workflow_ref, 'vars.MINT_RUNNER_ENABLED': enabled,
              'vars.MINT_RUNNER_ACCESS_READY': ready, 'github.sha': sha,
              'vars.MINT_RUNNER_APPROVED_SHA': approved}
    for key in sorted(values, key=len, reverse=True):
        expression = expression.replace(key, repr(values[key]))
    return eval(expression.replace('&&', ' and '), {'__builtins__': {}}, {})


class InventoryPolicy(unittest.TestCase):
    def test_default_and_partial_configuration_stay_disabled(self):
        job = load('mint-host-inventory.yml')['jobs']['inventory']
        self.assertFalse(allowed(job))
        full = dict(enabled='true', ready='verified', approved='a'*40)
        self.assertTrue(allowed(job, **full))
        for key in full:
            partial = dict(full); partial[key] = ''
            self.assertFalse(allowed(job, **partial), key)
        for change in [dict(event='pull_request'), dict(event='push'),
                       dict(event='workflow_call'), dict(ref='refs/heads/feature'),
                       dict(repo='fork/repo'), dict(workflow_ref='another/workflow'),
                       dict(approved='b'*40), dict(enabled='True'), dict(ready='true')]:
            self.assertFalse(allowed(job, **dict(full, **change)))

    def test_inventory_is_fixed_read_only_and_separately_approved(self):
        w = load('mint-host-inventory.yml')
        self.assertEqual(w['on'], {'workflow_dispatch': ''})
        self.assertEqual(w['permissions'], {})
        self.assertEqual(w['concurrency']['cancel-in-progress'], 'false')
        self.assertEqual(set(w['jobs']), {'inventory'})
        job = w['jobs']['inventory']
        self.assertEqual(job['environment'], 'mint-host-access')
        self.assertEqual(job['runs-on'], {'group': 'org/sde-mint-isolated', 'labels': 'sde-mint-inventory'})
        self.assertEqual(job['timeout-minutes'], '5')
        self.assertEqual(len(job['steps']), 1)
        step = job['steps'][0]
        self.assertNotIn('uses', step)
        source = step['run']
        self.assertNotIn('${{', source)
        self.assertNotRegex(source, r'sudo|apt-get|pkexec|curl|checkout|config.sh|run.sh|tauri|--execute')
        tree = ast.parse(source.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0])
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'run']
        self.assertEqual(len(calls), 1)
        self.assertEqual(ast.literal_eval(calls[0].args[0]), ['/usr/bin/qemu-system-x86_64', '--version'])

    def test_focused_checks_never_use_spare_host(self):
        w = load('mint-host-inventory-checks.yml')
        self.assertEqual(set(w['on']), {'pull_request', 'push'})
        self.assertEqual(w['permissions'], {'contents': 'read'})
        self.assertEqual(w['jobs']['policy']['runs-on'], 'ubuntu-24.04')
        for step in w['jobs']['policy']['steps']:
            self.assertNotIn('mint-host-access', str(step))
            self.assertNotIn('secrets.', str(step))
            self.assertNotIn('workflow run', str(step))
        for path in MINT_INFRA_PATHS:
            self.assertFalse(application_required([path]))
            self.assertTrue(application_required([path, 'installer/src/App.tsx']))


if __name__ == '__main__':
    unittest.main()
