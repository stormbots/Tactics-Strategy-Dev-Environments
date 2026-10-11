# Required native test: only a disposable CI runner; no release publication.
param([Parameter(Mandatory)][string]$FixtureRoot,[Parameter(Mandatory)][string]$TestExecutable)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable runner required.' }
$root = 'C:\ProgramData\SdeNativeSelfUpdateTest'
$acl = New-Object Security.AccessControl.DirectorySecurity
$acl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)')
[IO.Directory]::CreateDirectory($root,$acl) | Out-Null
Copy-Item -LiteralPath (Join-Path $FixtureRoot 'Skyview-Dev-Setup-Windows-x64.exe') -Destination $root
Copy-Item -LiteralPath $TestExecutable -Destination (Join-Path $root 'native-tests.exe')
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
    Set-Content (Join-Path $root 'done') 'PASS'
} catch { Write-Output $_; Set-Content (Join-Path $root 'done') 'FAIL'; exit 1 }
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
    if (-not (Select-String -LiteralPath (Join-Path $root 'native-upgrade.txt') -Pattern 'SDE_SIGNED_SYSTEM_UPGRADE_OK')) { throw 'Required native test did not execute.' }
} finally {
    # Removing the fixture task does not kill its running worker or packages.
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
