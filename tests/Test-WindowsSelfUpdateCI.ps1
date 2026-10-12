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
    $env:SDE_NATIVE_UPGRADE_FIXTURE = $root
    & (Join-Path $root 'native-tests.exe') --exact windows_install::native::tests::signed_upgrade_under_system --nocapture
    if ($LASTEXITCODE -ne 0) { throw 'Native signed upgrade test failed.' }
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
} finally {
    # Removing the fixture task does not kill its running worker or packages.
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
