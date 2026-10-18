"""Static and pure local checks; no runner registration, startup or remote mutation."""
import ast
import copy
from pathlib import Path
import unittest
import yaml
from runner_setup.group_policy import REPO, WORKFLOW, validate

ROOT = Path(__file__).resolve().parents[1]


class RunnerSetup(unittest.TestCase):
    def test_group_policy_and_each_fail_closed_field(self):
        good = dict(name='sde-mint-isolated', visibility='selected',
                    allows_public_repositories=True, restricted_to_workflows=True,
                    default=False, selected_workflows=[WORKFLOW])
        repos = {'total_count': 1, 'repositories': [{'full_name': REPO, 'private': False}]}
        self.assertEqual(validate(good, repos, 'a'*40), [])
        for key in good:
            bad = copy.deepcopy(good)
            bad.pop(key)
            self.assertIn(key, validate(bad, repos, 'a'*40))
        for workflows in [[], [WORKFLOW, 'other'], [WORKFLOW.replace('main', 'feature')]]:
            self.assertIn('selected_workflows', validate(dict(good, selected_workflows=workflows), repos, 'a'*40))
        for bad in [{}, dict(repos, total_count=2), dict(repos, repositories=[]),
                    {'total_count': 1, 'repositories': [{'full_name': 'other', 'private': False}]}]:
            self.assertIn('selected_repositories', validate(good, bad, 'a'*40))
        self.assertIn('approved_sha', validate(good, repos, 'main'))
        self.assertIn('restricted_to_workflows', validate(dict(good, restricted_to_workflows=1), repos, 'a'*40))

    def test_template_boundaries_and_embedded_python(self):
        source = (ROOT/'docs/design/runner-setup/mint-host-inventory.yml.template').read_text()
        w = yaml.load(source, Loader=yaml.BaseLoader)
        self.assertEqual(set(w['on']), {'workflow_dispatch'})
        self.assertEqual(w['permissions'], {})
        self.assertEqual(set(w['jobs']), {'inventory'})
        job = w['jobs']['inventory']
        self.assertEqual(job['runs-on'], {'group': 'org/sde-mint-isolated', 'labels': 'sde-mint-inventory'})
        self.assertEqual(job['environment'], 'mint-host-access')
        self.assertEqual(job['timeout-minutes'], '5')
        self.assertIn('github.sha == vars.MINT_RUNNER_APPROVED_SHA', job['if'])
        self.assertIn("github.ref == 'refs/heads/main'", job['if'])
        self.assertEqual(len(job['steps']), 1)
        step = job['steps'][0]
        self.assertNotIn('uses', step)
        run = step['run']
        self.assertNotIn('${{', run)
        self.assertNotRegex(run, r'sudo|apt-get|pkexec|curl|checkout|config.sh|run.sh|tauri|--execute')
        ast.parse(run.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0])
        self.assertNotIn('workflow_call', w['on'])


if __name__ == '__main__':
    unittest.main()
