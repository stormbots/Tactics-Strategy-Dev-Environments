"""Static/pure policy checks only: never open KVM or execute inventory code."""
import ast
from pathlib import Path
import unittest
import yaml
from ci_scope import APPLICATION_JOBS, GATE, MINT_INFRA_PATHS, application_required

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

    def test_preparation_checks_are_automatic_mocked_only(self):
        w = load('mint-host-inventory-checks.yml')
        self.assertEqual(set(w['jobs']), {'policy'})
        job = w['jobs']['policy']
        self.assertNotIn('environment', job)
        self.assertEqual(job['timeout-minutes'], '5')
        self.assertEqual(w['on']['push']['branches'], ['main'])
        for event in ('pull_request', 'push'):
            self.assertEqual(set(w['on'][event]['paths']),
                             MINT_INFRA_PATHS | {'tests/fixtures/linuxmint-iso-signing.asc'})
        commands = [s['run'] for s in job['steps'] if 'run' in s]
        self.assertEqual(commands, ["python3 -m pip install 'PyYAML==6.0.2'",
            'python3 -m unittest discover -s tests -p test_mint_host_inventory.py -v\n'
            'python3 -m unittest discover -s tests -p test_ci_scope.py -v\n'
            'python3 -m unittest discover -s tests -p test_mint_media_console.py -v\n'
            'python3 -m unittest discover -s tests -p test_mint_media_workflow.py -v\n'
            'python3 -m unittest discover -s tests -p test_mint_runner_permissions.py -v\n'
            'python3 -m unittest discover -s tests -p test_mint_checkout_observer.py -v\n'
            'python3 -m unittest discover -s tests -p test_mint_session_archive_plan.py -v\n'])
        self.assertEqual(job['steps'][0]['with']['persist-credentials'], 'false')

    def test_scope_exception_does_not_expand_to_native_or_application_work(self):
        for path in ('tests/fixtures/linuxmint-iso-signing.asc',
                     'tests/mint_media_other.py',
                     '.github/workflows/mint-media-prepare.yml',
                     'installer/src/App.tsx', 'backend/linux/self-update.py'):
            self.assertTrue(application_required([path]), path)
            self.assertTrue(application_required(['tests/mint_media_native.py', path]), path)

    def test_actual_installer_jobs_require_positive_scope_result(self):
        w = load('build-dev-setup.yml')
        for name in APPLICATION_JOBS:
            self.assertEqual(w['jobs'][name]['needs'], 'scope')
            self.assertEqual(w['jobs'][name]['if'], GATE)
        self.assertEqual(set(w['jobs']), {'scope', *APPLICATION_JOBS, 'release'})
        self.assertEqual(set(w['jobs']['release']['needs']), set(APPLICATION_JOBS))
        self.assertNotIn('always()', w['jobs']['release']['if'])
        scope = w['jobs']['scope']
        self.assertEqual(scope['outputs']['application_required'],
                         '${{ steps.scope.outputs.application_required }}')
        self.assertTrue(any(step.get('id') == 'scope' and
                            step.get('run') == 'python3 tests/ci_scope.py'
                            for step in scope['steps']))

    def test_native_fixture_jobs_require_explicit_dispatch_and_opt_in(self):
        w = load('native-uat-fixtures.yml')
        self.assertEqual(set(w['on']), {'push', 'pull_request', 'workflow_dispatch'})
        inputs = w['on']['workflow_dispatch']['inputs']
        self.assertEqual(set(inputs), {'run_native'})
        self.assertEqual(inputs['run_native']['type'], 'boolean')
        self.assertEqual(inputs['run_native']['default'], 'false')
        self.assertEqual(inputs['run_native']['required'], 'true')
        self.assertEqual(w['permissions'], {'contents': 'read'})
        self.assertEqual(set(w['jobs']), {'workflow-checks', 'windows-fixtures', 'mint-fixtures'})
        for name, runner in [('windows-fixtures', 'windows-2022'),
                             ('mint-fixtures', 'ubuntu-24.04')]:
            job = w['jobs'][name]
            self.assertEqual(job['needs'], 'workflow-checks')
            self.assertEqual(job['runs-on'], runner)
            expression = job['if']
            self.assertEqual(expression, "github.event_name == 'workflow_dispatch' && "
                "github.repository == 'stormbots/Tactics-Strategy-Dev-Environments' && inputs.run_native == true")
            for event in ('pull_request', 'pull_request_target', 'push', 'workflow_run', 'workflow_call', 'workflow_dispatch'):
                for repo in ('stormbots/Tactics-Strategy-Dev-Environments', 'fork/repo'):
                    for opt_in in (False, True):
                        check = expression.replace('github.event_name', repr(event)).replace(
                            'github.repository', repr(repo)).replace('inputs.run_native', repr(opt_in))
                        result = eval(check.replace('&&', ' and ').replace('== true', '== True'),
                                      {'__builtins__': {}}, {})
                        self.assertEqual(result, event == 'workflow_dispatch' and
                            repo == 'stormbots/Tactics-Strategy-Dev-Environments' and opt_in)

    def test_automatic_fixture_job_is_static_only(self):
        w = load('native-uat-fixtures.yml')
        job = w['jobs']['workflow-checks']
        self.assertEqual(job['runs-on'], 'ubuntu-24.04')
        self.assertEqual(job['timeout-minutes'], '5')
        self.assertNotIn('environment', job)
        self.assertEqual(len(job['steps']), 2)
        self.assertEqual(job['steps'][0], {'uses': 'actions/checkout@v4'})
        self.assertEqual(job['steps'][1]['uses'], 'docker://rhysd/actionlint:1.7.7')
        self.assertEqual(job['steps'][1]['with']['args'],
            '-color .github/workflows/build-dev-setup.yml .github/workflows/native-uat-fixtures.yml')
        self.assertNotIn('run', job['steps'][1])
        # Gate policy changes receive automatic static/mocked validation too.
        for event in ('pull_request', 'push'):
            self.assertIn('.github/workflows/native-uat-fixtures.yml',
                load('mint-host-inventory-checks.yml')['on'][event]['paths'])


if __name__ == '__main__':
    unittest.main()
