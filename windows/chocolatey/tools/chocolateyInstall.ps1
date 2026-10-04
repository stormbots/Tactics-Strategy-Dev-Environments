$ErrorActionPreference = 'Stop'

Write-Host 'Configuring Skyview Robotics Windows development workstation...'

# Persistent team data/scripts.
$Skyview = 'C:\ProgramData\SkyviewRobotics'
$Logs = Join-Path $Skyview 'Logs'
New-Item -ItemType Directory -Path $Skyview -Force | Out-Null
New-Item -ItemType Directory -Path $Logs -Force | Out-Null
New-Item -ItemType Directory -Path 'C:\Development' -Force | Out-Null

$Tools = Split-Path -Parent $MyInvocation.MyCommand.Definition
foreach ($file in @(
    'AutoUpdate-SkyviewTools.ps1',
    'Update-SkyviewTools.ps1',
    'Update-Node24.ps1',
    'Setup-SkyviewRepositories.ps1',
    'Test-SkyviewStudentDev.ps1',
    'extensions.txt',
    'repositories.csv'
)) {
    Copy-Item (Join-Path $Tools $file) (Join-Path $Skyview $file) -Force
}

# Windows developer settings: deliberately minimal.
$fsKey = 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem'
Set-ItemProperty -Path $fsKey -Name LongPathsEnabled -Type DWord -Value 1

$appUnlock = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock'
New-Item -Path $appUnlock -Force | Out-Null
Set-ItemProperty -Path $appUnlock -Name AllowDevelopmentWithoutDevLicense -Type DWord -Value 1

$explorer = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'
New-Item -Path $explorer -Force | Out-Null
Set-ItemProperty -Path $explorer -Name HideFileExt -Type DWord -Value 0

# Windows OpenSSH client. No SSH server is enabled.
$ssh = Get-WindowsCapability -Online -Name 'OpenSSH.Client*' -ErrorAction SilentlyContinue
if ($ssh -and $ssh.State -ne 'Installed') {
    Add-WindowsCapability -Online -Name $ssh.Name | Out-Null
}

if (Get-Command Update-SessionEnvironment -ErrorAction SilentlyContinue) {
    Update-SessionEnvironment
}

# Git defaults. Identity and GitHub authentication are intentionally untouched.
if (Get-Command git.exe -ErrorAction SilentlyContinue) {
    git config --system core.longpaths true
    git config --global init.defaultBranch main
    git config --global fetch.prune true
}

# Pin Node. Mentor-run Update-Node24.ps1 is the only normal runtime update path.
$choco = 'C:\ProgramData\chocolatey\bin\choco.exe'
if (Test-Path $choco) {
    & $choco pin add --name=nodejs-lts | Out-Null
}

# VSCodium profile configuration. Because the only Windows account is the shared
# local-admin account, installing elevated still targets the same user profile.
$codium = Get-Command codium -ErrorAction SilentlyContinue
if (-not $codium) {
    $candidates = @(
        'C:\Program Files\VSCodium\bin\codium.cmd',
        'C:\Program Files\VSCodium\bin\codium.exe',
        "$env:LOCALAPPDATA\Programs\VSCodium\bin\codium.cmd"
    ) | Where-Object { Test-Path $_ }
    if ($candidates) { $codiumPath = $candidates[0] }
} else { $codiumPath = $codium.Source }

if ($codiumPath) {
    foreach ($ext in (Get-Content (Join-Path $Tools 'extensions.txt') | Where-Object { $_ })) {
        Write-Host "Installing VSCodium extension $ext"
        & $codiumPath --install-extension $ext --force
        if ($LASTEXITCODE -ne 0) { Write-Warning "Extension install failed: $ext" }
    }
} else {
    Write-Warning 'VSCodium CLI was not found during package installation. Run Test-SkyviewStudentDev.ps1 after sign-out/sign-in.'
}

$settingsDir = Join-Path $env:APPDATA 'VSCodium\User'
New-Item -ItemType Directory -Path $settingsDir -Force | Out-Null
Copy-Item (Join-Path $Tools 'settings.json') (Join-Path $settingsDir 'settings.json') -Force

# Weekly automatic updates for non-runtime tooling. Browsers and Windows retain
# their native updater behavior; Node is deliberately excluded.
$taskName = 'Skyview Robotics - Dev Tool Updates'
$script = Join-Path $Skyview 'AutoUpdate-SkyviewTools.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -User 'SYSTEM' -RunLevel Highest -Force | Out-Null

Write-Host ''
Write-Host 'Skyview Robotics development workstation baseline installed.'
Write-Host 'Node.js is pinned to major 24 and Git/GitHub identity is intentionally unconfigured.'
Write-Host 'Run C:\ProgramData\SkyviewRobotics\Test-SkyviewStudentDev.ps1 to validate.'
