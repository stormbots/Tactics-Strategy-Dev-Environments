# Destructive installation probe: run ONLY on a disposable Windows CI runner.
param([Parameter(Mandatory)][string]$InstallerRoot, [switch]$UatPair)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub Actions runner required.' }
$InstallerRoot = (Resolve-Path $InstallerRoot).Path
$worker = Join-Path $InstallerRoot 'worker.ps1'
$result = Join-Path $InstallerRoot 'windows.txt'
$done = Join-Path $InstallerRoot 'done.txt'
$script = @'
param([string]$Root, [switch]$UatPair)
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
    $versions = if ($UatPair) { @('1.2.2', '1.2.3') } else { @('1.2.0', '1.2.1') }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.4/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions += '1.2.4' }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.5/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions += '1.2.5' }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.6/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions += '1.2.6' }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.7/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions += '1.2.7' }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.8/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions = @('1.2.7', '1.2.8') }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.9/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions = @('1.2.8', '1.2.9') }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.10/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions = @('1.2.9', '1.2.10') }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.11/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions = @('1.2.10', '1.2.11') }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.12/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions = @('1.2.11', '1.2.12') }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.13/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions = @('1.2.12', '1.2.13') }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.14/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions = @('1.2.13', '1.2.14') }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.15/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions = @('1.2.14', '1.2.15') }
    if ($UatPair -and (Test-Path (Join-Path $Root '1.2.16/Skyview-Dev-Setup-Windows-x64.exe'))) { $versions = @('1.2.15', '1.2.16') }
    $settings = 'C:\Development\.vscode\settings.json'
    New-Item -ItemType Directory -Force (Split-Path $settings) | Out-Null
    Set-Content $settings '{"editor.fontSize":17}'
    $settingsBefore = Get-Content $settings -Raw
    $legacyBaseline = 'C:\ProgramData\SkyviewRobotics\Update-SkyviewTools.ps1'
    foreach ($version in $versions) {
        if ($UatPair -and $version -eq $versions[1]) {
            Set-Content $legacyBaseline '# legacy maintenance UAT sentinel'
            if ($version -eq '1.2.16') {
                & 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe' pause
                if ($LASTEXITCODE -ne 0) { throw 'Could not prepare paused prior installation.' }
            }
        }
        $exe = Join-Path $Root "$version\Skyview-Dev-Setup-Windows-x64.exe"
        $flags = if ($version -ne $versions[0]) { '/S /UPDATE' } else { '/S' }
        $process = Start-Process -FilePath $exe -ArgumentList $flags -PassThru
        if (-not $process.WaitForExit(300000)) { throw 'Installer exceeded five minutes; investigate runner, do not terminate production package transactions' }
        Write-Output "Installer $version flags=$flags exit=$($process.ExitCode)"
        if ($process.ExitCode -ne 0) { throw "Unexpected installer exit $($process.ExitCode)" }
        $app = 'C:\Program Files\Skyview Dev Setup\skyview-dev-setup.exe'
        if (-not (Test-Path $app)) { throw 'Expected per-machine executable absent' }
        $actual = (Get-Item $app).VersionInfo.ProductVersion
        Write-Output "Executable: $app version=$actual"
        if ($actual -notmatch ('^' + [regex]::Escape($version) + '($|\.)')) { throw 'Installed version mismatch' }
        if ($UatPair -and $version -eq '1.2.12') {
            $icon = "C:\Program Files\Skyview Dev Setup\app-icons\skyview-dev-setup-$version.ico"
            if (-not (Test-Path $icon)) { throw 'Versioned Windows icon absent' }
            $programs = [Environment]::GetFolderPath('CommonPrograms')
            $links = @(Get-ChildItem $programs -Filter 'Skyview Dev Setup.lnk' -Recurse)
            if ($links.Count -ne 1) { throw 'Expected one installed Start shortcut' }
            $shell = New-Object -ComObject WScript.Shell
            $link = $shell.CreateShortcut($links[0].FullName)
            Write-Output "Start shortcut target=$($link.TargetPath) icon=$($link.IconLocation)"
            if ($link.TargetPath -ne $app -or $link.IconLocation -ne "$icon,0") {
                throw 'Start shortcut does not use the versioned icon'
            }
        }
        $backend = 'C:\Program Files\Skyview Dev Setup\backend\windows\chocolatey\tools\AutoUpdate-SkyviewTools.ps1'
        if (-not (Test-Path $backend)) { throw 'Bundled maintenance resource absent' }
        if (Test-Path $maintenance) { throw 'App installation unexpectedly provisioned external maintenance' }
        if (Get-Process -Name skyview-dev-setup -ErrorAction SilentlyContinue) { throw 'Installer launched GUI under SYSTEM' }
        if ((Get-Content $project -Raw).Trim() -ne 'student preservation sentinel') { throw 'Student file changed' }
        if ((Get-Content $settings -Raw) -ne $settingsBefore) { throw 'Settings changed' }
        if ($UatPair) {
            $rootPolicy = 'C:\ProgramData\SkyviewRobotics\SelfUpdate'
            $policy = Get-Content (Join-Path $rootPolicy 'policy.json') -Raw | ConvertFrom-Json
            $active = Get-Content (Join-Path $rootPolicy 'active.json') -Raw | ConvertFrom-Json
            if ($policy.paused -ne $false -or $active.version -ne $version) { throw 'Enabled policy or active engine mismatch' }
            if ($version -eq '1.2.16') {
                $policyWorker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
                foreach ($verb in @('pause','resume')) {
                    & $policyWorker $verb
                    if ($LASTEXITCODE -ne 0) { throw 'Administrator pause/resume failed.' }
                    $repeat = Start-Process -FilePath $exe -ArgumentList '/S /UPDATE' -Wait -PassThru -WindowStyle Hidden
                    if ($repeat.ExitCode -ne 0 -or (Get-Content (Join-Path $rootPolicy 'policy.json') -Raw | ConvertFrom-Json).paused -ne $false) { throw 'Installer did not enable updates from prior policy state.' }
                    if ((Get-Content $project -Raw).Trim() -ne 'student preservation sentinel' -or (Get-Content $settings -Raw) -ne $settingsBefore) { throw 'Repeated policy upgrade changed student state.' }
                }
                Write-Output 'SDE_UAT_ENABLED_DEFAULTS_WINDOWS_OK'
            }
            if ($version -eq $versions[0]) {
                if (Test-Path $legacyBaseline) { throw 'Unexpected applied baseline' }
            } else {
                if ((Get-Content $legacyBaseline -Raw).Trim() -ne '# legacy maintenance UAT sentinel') { throw 'Legacy baseline changed' }
                $worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
                $coordination = & $worker coordination-status | ConvertFrom-Json
                if ($LASTEXITCODE -ne 0 -or $coordination -ne 'needs_repair') { throw 'Legacy installation must require explicit Repair' }
            }
            if (Get-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates' -ErrorAction SilentlyContinue) { throw 'Unexpected tool schedule' }
        }
        Write-Output 'PASS: version, resources, no provisioning, no GUI launch, student marker'

    }
    if ($UatPair) { Write-Output 'SDE_UAT_PAIR_WINDOWS_OK' }
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
$pairFlag = if ($UatPair) { ' -UatPair' } else { '' }
$action.Arguments += $pairFlag
Register-ScheduledTask -TaskName $task -Action $action -User SYSTEM -RunLevel Highest -Force | Out-Null
try {
    Start-ScheduledTask -TaskName $task
    $minutes = if ($UatPair -and (Test-Path (Join-Path $InstallerRoot '1.2.8/Skyview-Dev-Setup-Windows-x64.exe'))) { 11 } elseif ($UatPair -and (Test-Path (Join-Path $InstallerRoot '1.2.7/Skyview-Dev-Setup-Windows-x64.exe'))) { 31 } elseif ($UatPair -and (Test-Path (Join-Path $InstallerRoot '1.2.6/Skyview-Dev-Setup-Windows-x64.exe'))) { 26 } elseif ($UatPair -and (Test-Path (Join-Path $InstallerRoot '1.2.5/Skyview-Dev-Setup-Windows-x64.exe'))) { 21 } elseif ($UatPair -and (Test-Path (Join-Path $InstallerRoot '1.2.4/Skyview-Dev-Setup-Windows-x64.exe'))) { 16 } else { 11 }
    $deadline = (Get-Date).AddMinutes($minutes)
    while (-not (Test-Path $done) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 2 }
    if (Test-Path $result) { Get-Content $result }
    if (-not (Test-Path $done)) { throw 'SYSTEM probe timed out' }
    if ((Get-Content $done).Trim() -ne 'PASS') { throw 'SYSTEM probe failed; inspect transcript' }
} finally { Unregister-ScheduledTask -TaskName $task -Confirm:$false }
