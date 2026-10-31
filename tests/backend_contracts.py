"""Read-only regression checks for the provisioning safety contract."""
from pathlib import Path
import importlib.util
import hashlib
import re, unittest
import stat
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class Backends(unittest.TestCase):
    def text(self,p): return (ROOT/p).read_text(encoding='utf-8-sig')
    def test_recovery_reports_are_user_artifacts_not_acknowledgment_authority(self):
        source = self.text('installer/src-tauri/src/recovery_summary.rs')
        self.assertIn('.app_data_dir()', source)
        self.assertIn('.join("recovery-reports")', source)
        self.assertIn('support::redact_home(app', source)
        self.assertIn('if !confirmed', source)
        self.assertNotIn('choose_path', source)
        reports_only = source.split('pub async fn acknowledge_recovery_incident', 1)[0]
        self.assertNotIn('recovery::submit', reports_only)
        self.assertNotIn('journal::acknowledge', source)
        storage = self.text('installer/src-tauri/src/recovery_reports.rs')
        self.assertIn('create_new(true)', storage)
        self.assertIn('Commit marker is last', storage)
        self.assertIn('Never overwrite a report ID', storage)
        self.assertIn('incomplete_or_unreadable', storage)
        self.assertIn('default-src', storage)
        self.assertIn('sde-report-ci-', storage)
        self.assertNotIn('sde_coordination::', storage)
        self.assertIn('../../installer/src-tauri/src/recovery_reports.rs', self.text('coordination/src/lib.rs'))
    def test_acknowledgment_controller_is_one_report_attempt_then_intent_not_execution(self):
        source = self.text('installer/src-tauri/src/recovery_summary.rs')
        controller = source.split('pub async fn acknowledge_recovery_incident', 1)[1].split('#[tauri::command]', 1)[0]
        self.assertIn('app.state::<crate::Busy>().enter()', controller)
        self.assertIn('recovery_acknowledgment::run(', controller)
        self.assertIn('recovery::submit(id).map_err(submission_error)', controller)
        self.assertNotIn('journal::acknowledge', controller)
        self.assertNotIn('record_acknowledgment(', controller)
        self.assertNotIn('mutation::', controller)
        self.assertNotIn('process::', controller)
        flow = self.text('installer/src-tauri/src/recovery_acknowledgment.rs')
        self.assertLess(flow.index('let snapshot = capture()?'), flow.index('match save(&snapshot)'))
        self.assertLess(flow.index('match save(&snapshot)'), flow.index('match submit(&incident_id)'))
        self.assertIn('Unconfirmed', flow)
        self.assertIn('summary.validate()?', source)
        self.assertIn('../../installer/src-tauri/src/recovery_acknowledgment.rs', self.text('coordination/src/lib.rs'))
    def test_recovery_context_is_fixed_read_only_diagnostic_provenance(self):
        source = self.text('installer/src-tauri/src/recovery_context.rs').split('#[cfg(test)]', 1)[0]
        self.assertIn('directory.join("operation-journal.json")', source)
        self.assertIn('MAX_RECORD + 1', source)
        self.assertIn('O_NOFOLLOW', source)
        self.assertIn('GetFileInformationByHandle', source)
        self.assertNotIn('fs::write', source)
        self.assertNotIn('set_permissions', source)
        self.assertNotIn('recovery::submit', source)
        capture = self.text('installer/src-tauri/src/recovery_summary.rs')
        self.assertIn('Source::User => recovery_context::read_user(', capture)
        self.assertIn('Source::Machine)', capture)
        self.assertIn('../../installer/src-tauri/src/recovery_context.rs', self.text('coordination/src/lib.rs'))
    def test_validation_timestamp_is_collected_natively_not_at_report_generation(self):
        source = self.text('installer/src-tauri/src/main.rs')
        self.assertIn('protocol::validation_time(', source)
        self.assertIn('validation_collected_at: Option<u64>', source)
        report = self.text('installer/src/supportReport.ts')
        self.assertNotIn('collectedAt: input.validationComplete ? new Date()', report)
        self.assertIn('input.validationCollectedAt', report)
    def test_user_acknowledgment_preserves_evidence_separately_from_reports_and_machine_authority(self):
        source = self.text('installer/src-tauri/src/recovery_user.rs').split('#[cfg(test)]', 1)[0]
        self.assertIn('.join("recovery-state")', source)
        self.assertIn('"evidence.json"', source)
        self.assertIn('"acknowledged.json"', source)
        self.assertIn('RENAME_NOREPLACE', source)
        self.assertIn('MOVEFILE_WRITE_THROUGH', source)
        self.assertNotIn('MOVEFILE_REPLACE_EXISTING', source)
        self.assertNotIn('remove_file', source)
        self.assertNotIn('sde_coordination', source)
        self.assertLess(source.index('publish(&directory, "evidence.json"'), source.index('"acknowledged.json",\n'))
        commands = self.text('installer/src-tauri/src/recovery_summary.rs')
        user = commands.split('pub async fn acknowledge_user_recovery_incident', 1)[1].split('pub async fn inspect_user_recovery_acknowledgment', 1)[0]
        self.assertIn('if !confirmed', user)
        self.assertIn('app.state::<crate::Busy>().enter()', user)
        self.assertIn('Source::User', user)
        self.assertIn('.with_report(', user)
        self.assertNotIn('recovery::submit', user)
        self.assertNotIn('journal::acknowledge', user)
        self.assertIn('../../installer/src-tauri/src/recovery_user.rs', self.text('coordination/src/lib.rs'))
    def test_linux_integrity_manifest_matches_shipped_sources(self):
        entries = dict(line.split(None, 1)[::-1] for line in self.text('linux/SHA256SUMS').splitlines() if line.strip())
        self.assertTrue({'./Validate-SkyviewStudentDev.sh', './lib/coordination.py', './lib/coordination.sh'}.issubset(entries))
        for name, expected in entries.items():
            self.assertEqual(hashlib.sha256((ROOT / 'linux' / name).read_bytes()).hexdigest(), expected, name)
    def test_canonical_extensions_match(self):
        self.assertEqual(self.text('linux/extensions.txt').splitlines(),self.text('windows/chocolatey/tools/extensions.txt').splitlines())
    def test_linux_user_boundary(self):
        user=self.text('linux/Configure-SkyviewUser.sh')
        self.assertNotRegex(user,r'\bsudo\b')
        self.assertIn('must not run as root',user)
        install=self.text('linux/Install-SkyviewStudentDev.sh')
        self.assertIn('"$SYSTEM_ONLY" != 1',install)
        # System Python runs coordination utilities; the student runtime stays 3.14.
        self.assertIn('python3.14 python3.14-venv', install)
        self.assertNotRegex(install, r'apt-get[^\n]*install[^\n]*\bpython3(?:\s|$)')
        update=self.text('linux/Update-SkyviewStudentDev.sh')
        self.assertNotRegex(update,r'apt-get\s+(dist-upgrade|upgrade|full-upgrade)')
        self.assertIn('"nodejs=$NODE_VERSION"',update)
        self.assertNotIn('install_codium_extensions_for_user',update)
    def test_no_identity_provisioning(self):
        for p in ['linux/Configure-SkyviewUser.sh','windows/chocolatey/tools/Configure-SkyviewUser.ps1']:
            self.assertNotRegex(self.text(p),r'git config[^\n]*(user\.name|user\.email)')
            self.assertNotIn('gh auth login',self.text(p))
    def test_privileged_interface(self):
        rust=self.text('installer/src-tauri/src/process.rs')
        self.assertIn('["install","repair","update"]',re.sub(r'\s+', '', rust))
        self.assertIn('parse_str(session)',rust)
        self.assertIn('debug_assertions',rust)
        self.assertIn('env_clear()',rust)
        cap=self.text('installer/src-tauri/capabilities/main.json')
        self.assertNotIn('shell:',cap)
        self.assertNotIn('fs:',cap)
    def test_release_gate(self):
        workflow=self.text('.github/workflows/build-dev-setup.yml')
        self.assertIn('needs: [checks, native, update-trust]',workflow)
        self.assertIn('environment: sde-release-signing',workflow)
        self.assertIn('dist/sde-update.json dist/sde-update.json.minisig',workflow)
        self.assertIn('--verify-tag --prerelease',workflow)
        self.assertIn('sha256sum --check',workflow)
        fallback=self.text('.github/workflows/publish-linux-v1.0.1.yml')
        self.assertIn('ref: linux-v1.0.1',fallback)
        self.assertNotIn('--clobber',fallback)
    def test_metadata_helpers_are_persisted(self):
        windows=self.text('windows/chocolatey/tools/chocolateyInstall.ps1')
        self.assertIn("'ToolRecords.ps1'",windows)
        self.assertIn("'Inspect-SkyviewSchedule.ps1'",windows)
        self.assertIn('"$SKYVIEW_LIB/tool_records.py"',self.text('linux/Install-SkyviewStudentDev.sh'))
    def test_scheduled_tools_use_one_shared_guard_before_application_work(self):
        for name in ('linux_install.rs', 'windows_install.rs'):
            source = self.text('updater/src/' + name)
            tools = source.split('fn tool_maintenance()', 1)[1].split('pub fn maintain_', 1)[0]
            self.assertIn('crate::tool_coordination::run(supervisor).map(Some)', tools)
            after = source.split('report.tool_exit = tool_maintenance()?;', 1)[1]
            self.assertLess(after.index('tool_coordination::incomplete_outcome(report.tool_exit)'),
                            after.index('report.phase = crate::observation::Phase::Identity'))
        linux = self.text('updater/src/linux_install.rs')
        self.assertIn('.arg("--leased")', linux)
        # The leased child still requires real inherited descriptors, never the
        # flag alone, before copying any applied baseline file.
        child = self.text('linux/self-update/applied.py')
        self.assertLess(child.index('coord.check()'), child.index("snapshot = HERE / 'applied-baseline'"))
        guard = self.text('updater/src/tool_coordination.rs')
        self.assertIn('mutation::begin(mutation::Scope::System)', guard)
        self.assertLess(guard.index('inspection::collect()'), guard.index('guard.finish_known()'))
        self.assertNotIn('recovery::submit(', guard.split('#[cfg(all(test,', 1)[0])
    def test_scheduled_tool_native_proof_cannot_be_silently_skipped(self):
        marker = 'SDE_RECOVERY_SCHEDULED_TOOL_CONTRACT_OK'
        self.assertIn('grep -Fxq ' + marker, self.text('tests/Test-LinuxSelfUpdateCI.sh'))
        windows = self.text('tests/Test-WindowsSelfUpdateCI.ps1')
        self.assertIn("-Pattern '^" + marker + r'\s*$', windows)
        for name in ('linux_install.rs', 'windows_install.rs'):
            self.assertIn('crate::tool_coordination::native_contracts();', self.text('updater/src/' + name))

    def test_application_installation_authenticates_before_recovery_and_retains_postchecks(self):
        for name in ('linux_install.rs', 'windows_install.rs'):
            source = self.text('updater/src/' + name)
            selected = source.split('fn install_selected(', 1)[1].split('fn prune', 1)[0]
            self.assertIn('Scope::Installation', selected)
            self.assertLess(selected.index('authenticate_staged('), selected.index('preparation.begin()'))
            self.assertLess(selected.index('preparation.begin()'), selected.index('guard.run('))
            self.assertLess(selected.index('guard.run('), selected.index('resources(&candidate.version)'))
            self.assertLess(selected.index('resources(&candidate.version)'), selected.index('installation_coordination::finish(guard)'))
            self.assertNotIn('lease.begin_transaction()', selected)
            self.assertIn('Scope::System', source.split('report.phase = crate::observation::Phase::Download', 1)[0])
            self.assertIn('if !operation.interrupted()', source)
            self.assertIn('report.recovery_available = if operation.interrupted()', source)
            self.assertIn('crate::installation_coordination::native_contracts(|authorized|', source)
        linux = self.text('updater/src/linux_install.rs').split('fn install_selected(', 1)[1].split('fn prune', 1)[0]
        self.assertNotIn('.arg("--audit")', linux)
        helper = self.text('updater/src/installation_coordination.rs').split('#[cfg(all(test,', 1)[0]
        self.assertIn('inspection::collect()', helper)
        self.assertIn('known_backend_completion(true, facts.activity, facts.health)', helper)
        self.assertNotIn('recovery::submit', helper)

    def test_signed_native_application_recovery_marker_is_required_on_both_platforms(self):
        marker = 'SDE_RECOVERY_APPLICATION_INSTALL_CONTRACT_OK'
        self.assertIn('grep -Fxq ' + marker, self.text('tests/Test-LinuxSelfUpdateCI.sh'))
        self.assertIn("-Pattern '^" + marker + r'\s*$', self.text('tests/Test-WindowsSelfUpdateCI.ps1'))
        helper = self.text('updater/src/installation_coordination.rs')
        self.assertIn('assert!(install(false).is_err())', helper)
        self.assertIn('Acknowledged signed native application upgrade must complete', helper)
        self.assertIn('Consent alone cannot prove the old process lifetime ended', helper)
        self.assertIn('Restart alone cannot replace consent', helper)
    def test_system_fixture_explicitly_receives_ci_context_before_native_execution(self):
        source = self.text('tests/Test-WindowsSelfUpdateCI.ps1')
        self.assertIn("if ($env:GITHUB_ACTIONS -ne 'true') { throw", source)
        worker = source.split("@'", 1)[1].split("'@ | Set-Content", 1)[0]
        indicator = "$env:GITHUB_ACTIONS = 'true'"
        self.assertEqual(worker.count(indicator), 1)
        self.assertLess(worker.index("throw 'Expected SYSTEM.'"), worker.index(indicator))
        self.assertLess(worker.index(indicator), worker.index("$env:SDE_NATIVE_UPGRADE_FIXTURE = $root"))
        self.assertLess(worker.index(indicator), worker.index("--exact windows_install::native::tests::signed_upgrade_under_system"))
        guard = self.text('updater/src/tool_coordination.rs')
        self.assertIn('assert_eq!(std::env::var("GITHUB_ACTIONS").as_deref(), Ok("true"))', guard)
    def test_native_fixture_establishes_inactivity_before_synthetic_journal(self):
        source = self.text('updater/src/tool_coordination.rs')
        fixture = source.split('pub(crate) fn native_contracts()', 1)[1]
        self.assertLess(fixture.index('await_native_fixture_inactivity('),
                        fixture.index('lease.begin_transaction()'))
        self.assertIn('let facts = inspection::collect();', fixture)
        self.assertIn('assert_eq!(run(command()).unwrap(), 0);', fixture)
        production = source.split('#[cfg(all(test,', 1)[0]
        self.assertNotIn('await_native_fixture_inactivity', production)
        self.assertNotIn('thread::sleep', production)
    def test_linux_outer_system_scripts_use_native_supervision_without_fallback(self):
        source = self.text('linux/lib/coordination.sh')
        self.assertLess(source.index('"$engine" check'), source.index('--supervise-linux-system'))
        native = source.split('elif [[ "$mode" == system ]]', 1)[1].split('\n  else', 1)[0]
        self.assertIn('/usr/bin/skyview-dev-setup --supervise-linux-system', native)
        self.assertNotIn('run "$mode"', native)
        self.assertIn('exit 76', native)
        self.assertIn('/usr/bin/skyview-dev-setup --coordination-init', native)
        self.assertIn('"$capability" != SDE_LINUX_SYSTEM_SUPERVISOR_V1', native)
        self.assertLess(native.index('--coordination-init'), native.index('--supervise-linux-system'))
        main = self.text('installer/src-tauri/src/main.rs')
        self.assertLess(main.index('--supervise-linux-system'), main.index('sde_coordination::session()'))
        self.assertIn('sde_coordination::manual::run(', main)
        native = self.text('coordination/src/manual.rs')
        self.assertIn('libc::geteuid()', native)
        self.assertIn('crate::validate_dir(', native)
        self.assertIn('known_backend_completion(status.success()', native)
        self.assertNotIn('recovery::submit(', native)
        marker = 'SDE_RECOVERY_LINUX_MANUAL_SUPERVISOR_OK'
        self.assertIn('grep -Fxq ' + marker, self.text('tests/Test-LinuxSelfUpdateCI.sh'))
        self.assertIn('grep -Fxq ' + marker, self.text('.github/workflows/build-dev-setup.yml'))

    def test_readonly_diagnosis_never_converts_validation_to_mutation_authority(self):
        validator = self.text('linux/Validate-SkyviewStudentDev.sh')
        self.assertIn('skyview_coordinate readonly "$@"', validator)
        engine = self.text('linux/lib/coordination.py')
        self.assertIn("if mode != 'readonly':", engine)
        self.assertIn("if mode == 'system':", engine)
        self.assertIn("'session', 'operation', 'system', 'readonly'", engine)
        self.assertIn('readonly_command(command)', engine)
        self.assertIn("path.name != 'Validate-SkyviewStudentDev.sh'", engine)
        shell = self.text('linux/lib/coordination.sh')
        self.assertLess(shell.index('engine=/usr/local/lib/skyview-student-dev/coordination.py'), shell.index('elif [[ "$mode" == readonly ]]'))
        self.assertIn('run readonly /bin/bash "$SCRIPT_DIR/$(basename -- "$0")"', shell)
        for source in (engine, self.text('windows/chocolatey/tools/Coordination.ps1')):
            self.assertIn('Validation does not acknowledge it or authorize changes', source)
        linux_marker = 'SDE_RECOVERY_LINUX_READONLY_VALIDATION_OK'
        self.assertIn(linux_marker, self.text('tests/verify_manual_recovery_native.py'))
        for path in ('tests/Test-LinuxSelfUpdateCI.sh', '.github/workflows/build-dev-setup.yml'):
            self.assertIn('grep -Fxq ' + linux_marker, self.text(path))
        windows_marker = 'SDE_RECOVERY_WINDOWS_READONLY_VALIDATION_OK'
        self.assertIn(windows_marker, self.text('tests/Test-CoordinationCI.ps1'))
        self.assertIn("$coordinationOutput -cnotcontains '" + windows_marker + "'", self.text('.github/workflows/build-dev-setup.yml'))
    def manual_fixture_module(self):
        spec = importlib.util.spec_from_file_location(
            'manual_native_fixture', ROOT / 'tests/verify_manual_recovery_native.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    def test_windows_install_repair_preserves_outer_and_nested_contracts(self):
        source = self.text('windows/Install-SkyviewStudentDev.ps1')
        self.assertIn("if ($SystemOnly) { $entryArguments += '-SystemOnly' }", source)
        self.assertIn("if ($Repair) { $entryArguments += '-Repair' }", source)
        self.assertIn('-Mutation -EntryPoint $PSCommandPath -EntryArguments $entryArguments -Action {', source)
        native = self.text('updater/src/manual_windows.rs')
        self.assertIn('Some("install-skyviewstudentdev.ps1")', native)
        self.assertIn('SHGetKnownFolderPath(', native)
        self.assertIn('token_member(WinLocalSystemSid) != Some(false)', native)
        self.assertIn('FOLDERID_RoamingAppData', native)
        self.assertIn('FOLDERID_LocalAppData', native)
        fixture = self.text('tests/Test-WindowsManualRecoveryCI.ps1')
        self.assertIn('SDE_RECOVERY_WINDOWS_MANUAL_INSTALL_REPAIR_OK', fixture)
        self.assertIn('Manual setup lost native current-account known folders.', fixture)
        self.assertIn('Unacknowledged incident was released.', fixture)
        baseline = self.text('tests/Test-Node24MigrationCI.ps1')
        self.assertIn('Invoke-SkyviewCoordinated -Mutation -Action {', baseline)
        self.assertIn('SKYVIEW_SYSTEM_SETUP_OK', baseline)

    def test_chocolatey_hook_requires_authenticated_parent_before_any_configuration(self):
        hook = self.text('windows/chocolatey/tools/chocolateyInstall.ps1')
        self.assertIn('Invoke-SkyviewCoordinated -Mutation -RequireParent -Action {', hook)
        self.assertLess(hook.index('-RequireParent'), hook.index("$Skyview = 'C:"))
        source = self.text('windows/chocolatey/tools/Coordination.ps1')
        parent = source.index('    if ($RequireParent) {')
        self.assertLess(source.index('if ($administrator -and $env:SKYVIEW_TRANSACTION_TOKEN)'), parent)
        self.assertLess(parent, source.index('if ($Mutation -and $EntryPoint)'))
        self.assertLess(parent, source.index('$session = $null; $operation = $null;'))
        self.assertIn('if (-not $RequireParent -and $global:SkyviewOperationLease', source)
        body = source[parent:].split('    if ($Mutation -and $EntryPoint)', 1)[0]
        self.assertIn('SDE_SUPERVISOR_REQUIRED:', body)
        self.assertNotIn('& $Action', body)
        self.assertNotIn('Remove-Item', body)
        self.assertIn('-Mutation -RequireParent -Action', self.text('tests/Invoke-RecoveryNestingCI.ps1'))
        workflow = self.text('.github/workflows/build-dev-setup.yml')
        self.assertIn("$coordinationOutput -cnotcontains 'SDE_WINDOWS_PACKAGE_HOOK_PARENT_REQUIRED_OK'", workflow)
    def test_windows_manual_maintenance_preserves_nested_proof_and_native_gates(self):
        source = self.text('windows/chocolatey/tools/Coordination.ps1')
        nested = source.index('if ($administrator -and $env:SKYVIEW_TRANSACTION_TOKEN)')
        outer = source.index('if ($Mutation -and $EntryPoint)')
        self.assertLess(nested, outer)
        body = source[outer:].split('    $session = $null;', 1)[0]
        self.assertIn("@('--coordination-init') -Capture", body)
        self.assertIn('SDE_WINDOWS_MAINTENANCE_SUPERVISOR_V1', body)
        self.assertIn('--supervise-windows-maintenance', body)
        self.assertIn('exit $result.ExitCode', body)
        self.assertNotIn('& $Action', body)
        self.assertNotIn('Remove-Item', body)
        self.assertIn('$process.StandardOutput.ReadLineAsync()', source)
        self.assertIn('$process.StandardError.ReadLineAsync()', source)
        self.assertNotIn('$process.Kill()', source)
        for name in ('Update-SkyviewTools.ps1', 'Update-Node24.ps1'):
            self.assertIn('-EntryPoint $PSCommandPath', self.text('windows/chocolatey/tools/' + name))
        adapter = self.text('updater/src/manual_windows.rs')
        self.assertIn('CheckTokenMembership(', adapter)
        self.assertIn('crate::host::validate(&current)', adapter)
        self.assertIn('info.nNumberOfLinks == 1', adapter)
        self.assertIn('sde_coordination::manual::run_trusted_backend(command)', adapter)
        self.assertNotIn('recovery::submit', adapter)
        self.assertNotIn('runas', adapter.lower())
        workflow = self.text('.github/workflows/build-dev-setup.yml')
        self.assertIn('Required Windows installed manual maintenance recovery', workflow)
        self.assertIn("$output -cnotcontains 'SDE_RECOVERY_WINDOWS_MANUAL_MAINTENANCE_OK'", workflow)
    def test_manual_fixture_requires_every_ancestor_to_be_protected(self):
        fixture = self.manual_fixture_module()
        self.assertEqual(fixture.FIXTURE_PARENT, Path('/var/lib'))
        source = self.text('tests/verify_manual_recovery_native.py')
        self.assertIn('dir=FIXTURE_PARENT', source)
        for invocation in ('require_protected_directory(FIXTURE_PARENT)',
                           'require_protected_script(script)',
                           'require_protected_script(install)'):
            self.assertIn(invocation, source)
        path = Path('/var/lib/sde-manual-ci-synthetic')
        good = SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o755)
        with patch.object(Path, 'lstat', autospec=True, return_value=good) as metadata:
            fixture.require_protected_directory(path)
        self.assertEqual([call.args[0] for call in metadata.call_args_list],
                         [path, *path.parents])
        for bad in (
            SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o777),
            SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o775),
            SimpleNamespace(st_uid=1000, st_mode=stat.S_IFDIR | 0o755),
            SimpleNamespace(st_uid=0, st_mode=stat.S_IFLNK | 0o755),
        ):
            # The leaf is private; an untrusted ancestor must STILL reject it.
            with patch.object(Path, 'lstat', autospec=True, side_effect=(
                lambda current, bad=bad: bad if current == Path('/var/lib') else good)):
                with self.assertRaisesRegex(AssertionError, 'ancestor ' + re.escape(str(Path('/var/lib'))) + ': uid='):
                    fixture.require_protected_directory(path)
    def test_manual_fixture_scripts_match_production_file_trust_shape(self):
        fixture = self.manual_fixture_module()
        path = Path('/var/lib/sde-manual-ci-synthetic/Update-SkyviewStudentDev.sh')
        directory = SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o755)
        good = SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o644, st_nlink=1)
        for info, allowed in (
            (good, True),
            (SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o664, st_nlink=1), False),
            (SimpleNamespace(st_uid=1000, st_mode=stat.S_IFREG | 0o644, st_nlink=1), False),
            (SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o644, st_nlink=2), False),
            (SimpleNamespace(st_uid=0, st_mode=stat.S_IFLNK | 0o644, st_nlink=1), False),
        ):
            with patch.object(Path, 'lstat', autospec=True, side_effect=(
                lambda current, info=info: info if current == path else directory)):
                if allowed:
                    fixture.require_protected_script(path)
                else:
                    with self.assertRaisesRegex(AssertionError, 'Untrusted manual fixture script'):
                        fixture.require_protected_script(path)
if __name__=='__main__': unittest.main()
