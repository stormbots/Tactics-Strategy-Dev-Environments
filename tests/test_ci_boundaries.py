"""Guard the actual workflow event/dispatch boundary without running packages."""
import itertools
from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    # BaseLoader preserves GitHub's `on` key instead of interpreting YAML 1.1 bools.
    return yaml.load((ROOT / '.github/workflows' / name).read_text(), Loader=yaml.BaseLoader)


def gate(expression, event, build=False, native=False, publish=False, ref='refs/heads/main',
         fixture=False, platform='all', runner='Windows'):
    values = {'github.event_name': event, 'github.ref': ref,
              'inputs.build_installers': build, 'inputs.run_native_packages': native,
              'inputs.publish_prerelease': publish, 'runner.os': runner,
              'inputs.build_linux_fixture_pair': fixture, 'inputs.installer_platform': platform}
    for key, value in values.items():
        expression = expression.replace(key, repr(value))
    expression = expression.replace('&&', ' and ').replace('||', ' or ')
    return bool(eval(expression, {'__builtins__': {}, 'startsWith': str.startswith}, {}))


class CiBoundaries(unittest.TestCase):
    def setUp(self):
        self.build = load('build-dev-setup.yml')
        self.uat = load('prepare-self-update-uat.yml')
        self.probe = load('probe-native-upgrade.yml')

    def test_installer_job_never_runs_automatically_even_with_truthy_inputs(self):
        expression = self.build['jobs']['native']['if']
        for event, build, native, publish in itertools.product(
                ['pull_request', 'push', 'workflow_dispatch'], [False, True], [False, True], [False, True]):
            with self.subTest(event=event, build=build, native=native, publish=publish):
                self.assertEqual(gate(expression, event, build, native, publish),
                                 event == 'workflow_dispatch' and build)

    def test_dispatch_defaults_cannot_build_install_or_publish(self):
        for name in ['build_installers', 'run_native_packages', 'publish_prerelease', 'build_linux_fixture_pair']:
            self.assertEqual(self.build['on']['workflow_dispatch']['inputs'][name]['default'], 'false')
        self.assertEqual(self.uat['on']['workflow_dispatch']['inputs']['publish_prerelease']['default'], 'false')
        self.assertFalse(gate(self.build['jobs']['native']['if'], 'workflow_dispatch'))
        self.assertFalse(gate(self.build['jobs']['release']['if'], 'workflow_dispatch', ref='refs/tags/v1.2.10'))

    def test_linux_artifact_selection_cannot_start_windows_packaging(self):
        import json
        expression = self.build['jobs']['native']['strategy']['matrix']['include']
        expression = expression.removeprefix('${{ fromJSON(').removesuffix(') }}')
        for selected, expected in [('linux', ['ubuntu-24.04']), ('windows', ['windows-2022']),
                                   ('all', ['windows-2022', 'ubuntu-24.04'])]:
            value = expression.replace('inputs.installer_platform', repr(selected))
            value = value.replace('&&', ' and ').replace('||', ' or ')
            matrix = json.loads(eval(value, {'__builtins__': {}}, {}))
            self.assertEqual([item['os'] for item in matrix], expected)
            for item in matrix:
                self.assertEqual(item['bundle'], 'deb' if item['os'] == 'ubuntu-24.04' else 'nsis')
        steps = self.build['jobs']['native']['steps']
        step = next(s for s in steps if s.get('name') == 'Build unpublished Linux app-only fixture pair without execution')
        self.assertFalse(gate(step['if'], 'workflow_dispatch', build=True, fixture=True, platform='linux'))
        self.assertTrue(gate(step['if'], 'workflow_dispatch', build=True, fixture=True, platform='linux', runner='Linux'))
        self.assertIn('--lib --no-run', step['run'])
        self.assertNotRegex(step['run'], r'--ignored|sudo|pkexec|apt-get|release create')
        validation = self.build['jobs']['scope']['steps'][0]['run']
        self.assertIn('test "$INSTALLER_PLATFORM" = linux', validation)
        self.assertIn('test "$RUN_NATIVE_PACKAGES" = false', validation)
        self.assertIn('test "$PUBLISH_PRERELEASE" = false', validation)
        self.assertIn('test "$INSTALLER_PLATFORM" = all', validation)
        baseline = next(s for s in steps if s.get('name') == 'Build unpublished Linux fixture baseline without downgrade')
        ordinary = next(s for s in steps if s.get('name') == 'Build native installer')
        self.assertIn('!inputs.build_linux_fixture_pair', ordinary['if'])
        self.assertEqual(baseline['if'], step['if'])
        self.assertIn('--write-configs', baseline['run'])
        self.assertIn('sde-app-only-configs/baseline.json', baseline['run'])
        self.assertIn('sde-app-only-configs/candidate.json', step['run'])
        self.assertNotRegex(baseline['run'], r'--ignored|sudo|pkexec|apt-get|release create')

    def test_native_package_and_registration_steps_require_separate_opt_in(self):
        jobs = self.build['jobs']
        patterns = r'--ignored|Test-CoordinationCI|Test-MaintenanceCI|Test-LegacyMaintenanceAclCI|Start-Process \$installer|Test-WindowsSelfUpdateCI|apt-get install -y ./dist/|Test-LinuxSelfUpdateCI|SDE_REQUIRE_SCHEDULE_SYSTEMD'
        checked = []
        for step in jobs['native']['steps']:
            if re.search(patterns, step.get('run', '')):
                self.assertIn('inputs.run_native_packages', step.get('if', ''), step.get('name'))
                self.assertFalse(gate(step['if'], 'workflow_dispatch', build=True))
                checked.append(step['name'])
        self.assertGreaterEqual(len(checked), 5)
        for job in ['checks', 'update-trust', 'desktop-check']:
            for step in jobs[job]['steps']:
                self.assertIsNone(re.search(patterns, step.get('run', '')), step.get('name'))
                self.assertNotIn('tauri build', step.get('run', ''))
                self.assertNotIn('choco pack', step.get('run', ''))
                self.assertNotIn('gh release create', step.get('run', ''))

    def test_publication_needs_explicit_dispatch_native_proof_and_signing_environment(self):
        job = self.build['jobs']['release']
        for event, build, native, publish in itertools.product(
                ['pull_request', 'push', 'workflow_dispatch'], [False, True], [False, True], [False, True]):
            self.assertEqual(gate(job['if'], event, build, native, publish, 'refs/tags/v1.2.10'),
                             event == 'workflow_dispatch' and build and native and publish)
        for ref in ['refs/heads/main', 'refs/heads/feat/example', 'refs/heads/release/v1.2.uat', 'refs/tags/v1.2.2', 'refs/tags/v1.2.3']:
            self.assertFalse(gate(job['if'], 'workflow_dispatch', True, True, True, ref))
        self.assertEqual(job['environment'], 'sde-release-signing')
        self.assertIn('native', job['needs'])
        job = self.uat['jobs']['sign-publish']
        self.assertEqual(job['environment'], 'sde-release-signing')
        self.assertFalse(gate(job['if'], 'workflow_dispatch'))
        self.assertTrue(gate(job['if'], 'workflow_dispatch', publish=True))
        self.assertFalse(gate(job['if'], 'pull_request', publish=True))

    def test_package_workflows_are_dispatch_only(self):
        self.assertEqual(set(self.uat['on']), {'workflow_dispatch'})
        self.assertEqual(set(self.probe['on']), {'workflow_dispatch'})

    def test_automatic_native_development_compilation_and_coordination_are_preserved(self):
        jobs = self.build['jobs']
        for name in ['desktop-check', 'update-trust']:
            self.assertEqual(jobs[name]['strategy']['matrix']['os'], ['ubuntu-24.04', 'windows-2022'])
            self.assertEqual(jobs[name]['if'], "needs.scope.outputs.application_required == 'true'")
        desktop = '\n'.join(s.get('run', '') for s in jobs['desktop-check']['steps'])
        self.assertIn('cargo check --locked --manifest-path installer/src-tauri/Cargo.toml --all-targets', desktop)
        self.assertIn('cargo test --locked --manifest-path installer/src-tauri/Cargo.toml', desktop)
        trust = '\n'.join(s.get('run', '') for s in jobs['update-trust']['steps'])
        self.assertIn('SDE_REQUIRE_COORDINATION=1', trust)
        self.assertIn('Test-AppUpdatePackageHooksLocal.ps1', trust)
        self.assertNotIn('cargo build --release', trust)
        steps = jobs['update-trust']['steps']
        coordination = next(s for s in steps if s.get('name') == 'Native cross-process coordination contracts')
        self.assertIn("runner.os == 'Windows' && '1'", coordination['env']['SDE_REQUIRE_COORDINATION'])

    def test_multi_command_rust_validation_is_fail_fast_on_windows(self):
        steps = self.build['jobs']['update-trust']['steps']
        for name in ['Native cross-process coordination contracts', 'Verifier formatting and static analysis']:
            step = next(s for s in steps if s.get('name') == name)
            # Explicit bash uses Actions' -e -o pipefail on both OSes. A later
            # successful command must not mask an earlier native tool failure.
            self.assertEqual(step.get('shell'), 'bash')

    def test_desktop_package_tests_are_ignored_without_explicit_dispatch(self):
        source = (ROOT / 'installer/src-tauri/src/process.rs').read_text()
        for name in ['github_runner_migrates_real_node26_to_node24_with_clean_environment',
                     'github_runner_installs_chocolatey_fixture_with_clean_environment']:
            match = re.search(r'#\[ignore = "Requires explicitly dispatched native package operations"\]\s+fn ' + name + r'\(\)\s*\{(.*?)let _guard', source, re.S)
            self.assertIsNotNone(match, name)
            self.assertIn('require_native_package_test();', match.group(1))
        self.assertIn('std::env::var("SDE_RUN_NATIVE_PACKAGES")', source)
        job = self.build['jobs']['native']
        step = next(s for s in job['steps'] if s.get('name') == 'Explicitly authorized desktop native package integration')
        self.assertIn('inputs.run_native_packages', step['if'])
        self.assertEqual(step['env']['SDE_RUN_NATIVE_PACKAGES'], '1')
        for step in self.build['jobs']['desktop-check']['steps']:
            self.assertNotIn('--ignored', step.get('run', ''))
            self.assertNotIn('SDE_RUN_NATIVE_PACKAGES', step.get('env', {}))
        guard = (ROOT / 'tests/Test-Node24MigrationCI.ps1').read_text().splitlines()[1]
        self.assertIn("$env:SDE_RUN_NATIVE_PACKAGES -ne '1'", guard)

    def test_mint_preflight_is_separate_read_only_and_mocks_are_automatic(self):
        workflow = load('mint-validation-preflight.yml')
        self.assertEqual(set(workflow['on']), {'pull_request', 'workflow_dispatch'})
        self.assertEqual(workflow['permissions'], {'contents': 'read'})
        self.assertEqual(set(workflow['jobs']), {'mocked-checks', 'host-preflight'})
        for job in workflow['jobs'].values():
            self.assertEqual(job['runs-on'], 'ubuntu-24.04')
            self.assertNotIn('needs', job)
            self.assertNotIn('permissions', job)
            self.assertEqual(job['timeout-minutes'], '5')
            for step in job['steps']:
                self.assertNotIn('secrets', str(step))
                run = step.get('run', '')
                self.assertNotRegex(run, r'sudo|apt-get|pkexec|workflow run|tauri build|qemu-system|--execute')
                if step.get('uses', '').startswith('actions/checkout@'):
                    self.assertEqual(step['with']['persist-credentials'], 'false')
        mock = workflow['jobs']['mocked-checks']['steps'][-1]['run']
        self.assertIn('test_mint_update_validation.py', mock)
        host = workflow['jobs']['host-preflight']['steps'][1]['run']
        self.assertIn("report['ready'] = False", host)
        self.assertIn('guest-execution-authorization', host)
        self.assertNotIn('verify_media(', host)
        self.assertNotIn('pip install', host)

    def test_only_publication_jobs_have_write_permission(self):
        for workflow, permitted in [(self.build, 'release'), (self.uat, 'sign-publish'), (self.probe, None)]:
            self.assertEqual(workflow['permissions']['contents'], 'read')
            for name, job in workflow['jobs'].items():
                if job.get('permissions', {}).get('contents') == 'write':
                    self.assertEqual(name, permitted)


if __name__ == '__main__':
    unittest.main()
