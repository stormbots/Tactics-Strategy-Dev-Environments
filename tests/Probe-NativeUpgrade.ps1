# Destructive installation probe: run ONLY on a disposable Windows CI runner.
param([Parameter(Mandatory)][string]$InstallerRoot)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub Actions runner required.' }
$InstallerRoot = (Resolve-Path $InstallerRoot).Path
$worker = Join-Path $InstallerRoot 'worker.ps1'
$result = Join-Path $InstallerRoot 'windows.txt'
$done = Join-Path $InstallerRoot 'done.txt'
$script = @'
param([string]$Root)
$ErrorActionPreference = 'Stop'
Start-Transcript -Path (Join-Path $Root 'windows.txt') -Force
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    if ($identity.User.Value -ne 'S-1-5-18') { throw 'Probe did not run as SYSTEM' }
    Write-Output "Identity: $($identity.Name)"
    $maintenance = 'C:\ProgramData\SkyviewRobotics\AutoUpdate-SkyviewTools.ps1'
    if (Test-Path $maintenance) { throw 'Runner already provisioned' }
    $project = 'C:\Development\sde-probe-student.txt'
    New-Item -ItemType Directory -Force (Split-Path $project) | Out-Null
    Set-Content $project 'student preservation sentinel'
    foreach ($version in @('1.2.0', '1.2.1')) {
        $exe = Join-Path $Root "$version\Skyview-Dev-Setup-Windows-x64.exe"
        $flags = if ($version -eq '1.2.1') { '/S /UPDATE' } else { '/S' }
        $process = Start-Process -FilePath $exe -ArgumentList $flags -PassThru
        if (-not $process.WaitForExit(300000)) { throw 'Installer exceeded five minutes; investigate runner, do not terminate production package transactions' }
        Write-Output "Installer $version flags=$flags exit=$($process.ExitCode)"
        if ($process.ExitCode -ne 0) { throw "Unexpected installer exit $($process.ExitCode)" }
        $app = 'C:\Program Files\Skyview Dev Setup\skyview-dev-setup.exe'
        if (-not (Test-Path $app)) { throw 'Expected per-machine executable absent' }
        $actual = (Get-Item $app).VersionInfo.ProductVersion
        Write-Output "Executable: $app version=$actual"
        if ($actual -notmatch ('^' + [regex]::Escape($version) + '($|\.)')) { throw 'Installed version mismatch' }
        $backend = 'C:\Program Files\Skyview Dev Setup\backend\windows\chocolatey\tools\AutoUpdate-SkyviewTools.ps1'
        if (-not (Test-Path $backend)) { throw 'Bundled maintenance resource absent' }
        if (Test-Path $maintenance) { throw 'App installation unexpectedly provisioned external maintenance' }
        if (Get-Process -Name skyview-dev-setup -ErrorAction SilentlyContinue) { throw 'Installer launched GUI under SYSTEM' }
        if ((Get-Content $project -Raw).Trim() -ne 'student preservation sentinel') { throw 'Student file changed' }
        Write-Output 'PASS: version, resources, no provisioning, no GUI launch, student marker'
    }
    Set-Content (Join-Path $Root 'done.txt') 'PASS'
} catch {
    Write-Output $_
    Set-Content (Join-Path $Root 'done.txt') 'FAIL'
    exit 1
} finally { Stop-Transcript }
'@
Set-Content $worker $script
$task = 'SDE disposable native upgrade probe'
$action = New-ScheduledTaskAction -Execute 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$worker`" -Root `"$InstallerRoot`""
Register-ScheduledTask -TaskName $task -Action $action -User SYSTEM -RunLevel Highest -Force | Out-Null
try {
    Start-ScheduledTask -TaskName $task
    $deadline = (Get-Date).AddMinutes(11)
    while (-not (Test-Path $done) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 2 }
    if (Test-Path $result) { Get-Content $result }
    if (-not (Test-Path $done)) { throw 'SYSTEM probe timed out' }
    if ((Get-Content $done).Trim() -ne 'PASS') { throw 'SYSTEM probe failed; inspect transcript' }
} finally { Unregister-ScheduledTask -TaskName $task -Confirm:$false }
