# Required native test: only a disposable CI runner; no release publication.
param([Parameter(Mandatory)][string]$FixtureRoot,[Parameter(Mandatory)][string]$TestExecutable)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable runner required.' }
$root = 'C:\ProgramData\SdeNativeSelfUpdateTest'
$acl = New-Object Security.AccessControl.DirectorySecurity
$acl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)')
[IO.Directory]::CreateDirectory($root,$acl) | Out-Null
Copy-Item -LiteralPath (Join-Path $FixtureRoot 'Skyview-Dev-Setup-Windows-x64.exe') -Destination $root
Copy-Item -LiteralPath (Join-Path $FixtureRoot 'sde-synthetic-failure.exe') -Destination $root
Copy-Item -LiteralPath $TestExecutable -Destination (Join-Path $root 'native-tests.exe')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '../dist/Skyview-Dev-Setup-Windows-x64.exe') -Destination (Join-Path $root 'legacy-parent-installer.exe')
# Preserve a customized disabled task through the packaging hook.
$maintenanceTask = 'Skyview Robotics - Dev Tool Updates'
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At 4:35am
Set-ScheduledTask -TaskName $maintenanceTask -Trigger $trigger | Out-Null
Disable-ScheduledTask -TaskName $maintenanceTask | Out-Null
$before = [xml](Export-ScheduledTask -TaskName $maintenanceTask)
$worker = Join-Path $root 'worker.ps1' 
@'
$ErrorActionPreference = 'Stop'
$root = 'C:\ProgramData\SdeNativeSelfUpdateTest'
Start-Transcript -Path (Join-Path $root 'native-upgrade.txt') -Force
try {
    if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne 'S-1-5-18') { throw 'Expected SYSTEM.' }
    # Model the observed legacy parent ACL before the real signed installer.
    # Existing file bytes remain protected. Reproduce the October 14 inherited
    # CI Write on Logs as well as the parent; no manual ACL repair is performed.
    $parent = 'C:\ProgramData\SkyviewRobotics'
    $legacyAcl = New-Object Security.AccessControl.DirectorySecurity
    $legacyAcl.SetSecurityDescriptorSddlForm('O:BAG:BAD:AI(A;OICIID;FA;;;SY)(A;OICIID;FA;;;BA)(A;OICIIOID;GA;;;CO)(A;OICIID;0x1200a9;;;BU)(A;CIID;DCLCRPCR;;;BU)')
    $baselineBefore = [IO.File]::ReadAllBytes((Join-Path $parent 'Update-SkyviewTools.ps1'))
    Set-Acl -LiteralPath $parent -AclObject $legacyAcl
    $logs = Join-Path $parent 'Logs'
    $logsAcl = New-Object Security.AccessControl.DirectorySecurity
    $logsAcl.SetSecurityDescriptorSddlForm('O:BAG:BAD:AI')
    Set-Acl -LiteralPath $logs -AclObject $logsAcl
    $legacyLog = Join-Path $logs 'AutoUpdate-20261014-051807.log'
    [IO.File]::WriteAllText($legacyLog,'Preserved legacy log fixture, not authenticated status.')
    $legacyLogAcl = New-Object Security.AccessControl.FileSecurity
    $legacyLogAcl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)')
    Set-Acl -LiteralPath $legacyLog -AclObject $legacyLogAcl
    $logBefore = [Convert]::ToBase64String([IO.File]::ReadAllBytes($legacyLog))
    $logAclBefore = (Get-Acl -LiteralPath $legacyLog).Sddl
    $policy = Join-Path $parent 'SelfUpdate\policy.json'
    $policyBefore = [Convert]::ToBase64String([IO.File]::ReadAllBytes($policy))
    $writers = @((Get-Acl -LiteralPath $logs).GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | Where-Object {
        $_.IdentityReference.Value -eq 'S-1-5-32-545' -and $_.IsInherited -and ($_.FileSystemRights -band [Security.AccessControl.FileSystemRights]::Write)
    })
    if ($writers.Count -ne 1 -or $writers[0].InheritanceFlags -ne [Security.AccessControl.InheritanceFlags]::ContainerInherit) { throw 'Native installer fixture did not reproduce inherited Logs write.' }
    # The automatic worker must continue to reject an untrusted parent. Model
    # mentor/elevated native application installation first; this packaging hook
    # must migrate permissions before the signed unattended worker can run.
    $migration = Start-Process (Join-Path $root 'legacy-parent-installer.exe') -ArgumentList '/S','/UPDATE' -Wait -PassThru
    if ($migration.ExitCode -ne 0) { throw 'SYSTEM application installation did not migrate legacy parent permissions.' }
    foreach ($rule in (Get-Acl -LiteralPath $logs).GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -eq 'S-1-5-32-545' -and ($rule.FileSystemRights -band [Security.AccessControl.FileSystemRights]::Write)) { throw 'Native installer left student write access on Logs.' }
    }
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($legacyLog)) -ne $logBefore -or (Get-Acl -LiteralPath $legacyLog).Sddl -ne $logAclBefore) { throw 'Native installer changed legacy log evidence/private permissions.' }
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($policy)) -ne $policyBefore) { throw 'Native migration changed application-update policy.' }
    Write-Output 'SDE_NATIVE_LEGACY_LOGS_ACL_OK'
    $env:SDE_NATIVE_UPGRADE_FIXTURE = $root
    & (Join-Path $root 'native-tests.exe') --exact windows_install::native::tests::signed_upgrade_under_system --nocapture
    if ($LASTEXITCODE -ne 0) { throw 'Native signed upgrade test failed.' }
    $parentAcl = Get-Acl -LiteralPath $parent
    foreach ($rule in $parentAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -eq 'S-1-5-32-545' -and ($rule.FileSystemRights -band [Security.AccessControl.FileSystemRights]::Write)) { throw 'Signed installer did not migrate legacy parent writes.' }
    }
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $parent 'Update-SkyviewTools.ps1'))) -ne [Convert]::ToBase64String($baselineBefore)) { throw 'Permission migration changed the tool baseline.' }
    Write-Output 'SDE_NATIVE_LEGACY_ACL_OK'
    # Verify the NEXT invocation uses the committed 1.2.2 engine. Tool work is
    # replaced only in this disposable fixture by a deterministic no-package
    # action, then restored. The worker is the real packaged production binary.
    $baseline = 'C:\ProgramData\SkyviewRobotics\Update-SkyviewTools.ps1'
    $bytes = [IO.File]::ReadAllBytes($baseline)
    $gui = [IO.File]::Open('C:\ProgramData\SkyviewRoboticsCoordination\sessions.gate','Open','Read','Read')
    try {
        $action = @"
# SDE_COORDINATION_V1
if (`$PSScriptRoot -notmatch '\\SelfUpdate\\runs\\[0-9a-f-]{36}\\applied-baseline$') { throw 'Maintenance did not snapshot the applied generation.' }
foreach (`$name in @('Coordination.ps1','Update-Node24.ps1','Node24.ps1')) {
    if ((Get-FileHash (Join-Path `$PSScriptRoot `$name)).Hash -ne (Get-FileHash (Join-Path 'C:\ProgramData\SkyviewRobotics' `$name)).Hash) { throw 'Applied policy snapshot differs.' }
}
`$held = `$false
try {
    `$probe = [IO.File]::Open('C:\ProgramData\SkyviewRoboticsCoordination\operations.gate','Open','Read','Read')
    `$probe.Dispose()
} catch [IO.IOException] {
    if ((`$_.Exception.HResult -band 0xffff) -ne 32) { throw }
    `$held = `$true
}
if (-not `$held -or -not `$env:SKYVIEW_TRANSACTION_TOKEN) { throw 'Supervisor lost its operation lease or private transaction.' }
exit 0
"@
        [IO.File]::WriteAllText($baseline, $action)
        & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File 'C:\ProgramData\SkyviewRobotics\SelfUpdate\Invoke-SkyviewMaintenance.ps1'
        # Server 2022 is intentionally ineligible for production discovery. The
        # native installation test above injects only a test authentication key.
        $status = Get-Content 'C:\ProgramData\SkyviewRobotics\SelfUpdate\status.json' -Raw | ConvertFrom-Json
        if ($status.maintenanceEngineVersion -ne '1.2.2' -or $status.toolExit -ne 0 -or $status.outcome -ne 'unavailable' -or $status.detail -notlike '*Unsupported*') { throw 'Next invocation did not use the new engine and independent tool outcome.' }
    } finally { $gui.Dispose(); [IO.File]::WriteAllBytes($baseline,$bytes) }
    Set-Content (Join-Path $root 'done') 'PASS' 
} catch {
    Write-Output $_
    foreach ($path in @('C:\Program Files\Skyview Dev Setup\sde-bootstrap.log','C:\Program Files\Skyview Dev Setup\backend\windows\self-update\bootstrap-error.log')) {
        if (Test-Path -LiteralPath $path) {
            Write-Output "Native hook diagnostic: $path"
            Write-Output (Get-Item -LiteralPath $path).LastWriteTimeUtc
            Get-Content -LiteralPath $path
        }
    }
    Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Skyview Dev Setup' -ErrorAction SilentlyContinue | Select-Object DisplayVersion,InstallLocation | ConvertTo-Json -Compress
    Set-Content (Join-Path $root 'done') 'FAIL'
    exit 1
}
finally { Stop-Transcript | Out-Null }
'@ | Set-Content -LiteralPath $worker -Encoding UTF8
$taskName = 'SDE disposable signed SYSTEM upgrade'
$action = New-ScheduledTaskAction -Execute 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$worker`""
Register-ScheduledTask -TaskName $taskName -Action $action -User SYSTEM -RunLevel Highest -Force | Out-Null
try {
    Start-ScheduledTask -TaskName $taskName
    $deadline = [DateTime]::UtcNow.AddMinutes(10)
    while (-not (Test-Path (Join-Path $root 'done')) -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Seconds 2 }
    if (Test-Path (Join-Path $root 'native-upgrade.txt')) { Get-Content (Join-Path $root 'native-upgrade.txt') }
    if (-not (Test-Path (Join-Path $root 'done'))) { throw 'Native test exceeded runner deadline; do not terminate package transactions.' }
    if ((Get-Content (Join-Path $root 'done')).Trim() -ne 'PASS') { throw 'SYSTEM native test failed.' }
    $after = [xml](Export-ScheduledTask -TaskName $maintenanceTask)
    foreach ($section in @('Triggers','Settings','Principals')) {
        if ($before.Task.$section.OuterXml -ne $after.Task.$section.OuterXml) { throw "Application upgrade changed task $section." }
    }
    if ($after.Task.Actions.Exec.Arguments -notlike '*SelfUpdate\Invoke-SkyviewMaintenance.ps1*') { throw 'Task did not migrate to the protected host.' }
    if (-not (Select-String -LiteralPath (Join-Path $root 'native-upgrade.txt') -Pattern 'SDE_SIGNED_SYSTEM_UPGRADE_OK')) { throw 'Required native test did not execute.' }
    if (-not (Select-String -LiteralPath (Join-Path $root 'native-upgrade.txt') -Pattern 'SDE_E2E_NATIVE_WINDOWS_OK')) { throw 'Required end-to-end native test did not execute.' }
} finally {
    # Removing the fixture task does not kill its running worker or packages.
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Test-SelfUpdateReadAccessCI.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Student self-update read-only access failed.' }
