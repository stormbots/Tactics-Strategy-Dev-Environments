$ErrorActionPreference = 'Continue'

$checks = @(
    @{Name='Git'; Command='git'; Args=@('--version')},
    @{Name='GitHub CLI'; Command='gh'; Args=@('--version')},
    @{Name='Node.js'; Command='node'; Args=@('--version')},
    @{Name='npm'; Command='npm'; Args=@('--version')},
    @{Name='VSCodium'; Command='codium'; Args=@('--version')},
    @{Name='PowerShell 7'; Command='pwsh'; Args=@('--version')}
)

$results = foreach ($check in $checks) {
    $cmd = Get-Command $check.Command -ErrorAction SilentlyContinue
    if ($cmd) {
        $out = & $check.Command @($check.Args) 2>&1 | Select-Object -First 1
        [pscustomobject]@{Tool=$check.Name; Status='OK'; Version=[string]$out}
    } else {
        [pscustomobject]@{Tool=$check.Name; Status='MISSING'; Version=''}
    }
}
$results | Format-Table -AutoSize

Write-Host ''
$node = (node --version 2>$null)
if ($node -and $node -match '^v24\.') { Write-Host "Node baseline: OK ($node)" } else { Write-Warning "Node baseline mismatch: $node (expected major 24)" }

Write-Host ''
Write-Host 'Git identity (intentionally not provisioned by Skyview package):'
$name = git config --global --get user.name 2>$null
$email = git config --global --get user.email 2>$null
Write-Host ('  user.name  : ' + $(if ($name) {$name} else {'<unset>'}))
Write-Host ('  user.email : ' + $(if ($email) {$email} else {'<unset>'}))

Write-Host ''
if (Get-Command gh.exe -ErrorAction SilentlyContinue) {
    & gh auth status *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host 'GitHub authentication: CONFIGURED'
    } else {
        Write-Host 'GitHub authentication: NOT CONFIGURED (expected)'
    }
} else {
    Write-Warning 'GitHub CLI is not installed, so authentication status cannot be checked.'
}

Write-Host ''
$devMode = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock' -Name AllowDevelopmentWithoutDevLicense -ErrorAction SilentlyContinue).AllowDevelopmentWithoutDevLicense
$longPaths = (Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
$fileExt = (Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced' -Name HideFileExt -ErrorAction SilentlyContinue).HideFileExt
Write-Host "Developer Mode registry setting : $devMode (expected 1)"
Write-Host "Long paths                   : $longPaths (expected 1)"
Write-Host "Hide file extensions         : $fileExt (expected 0)"

Write-Host ''
$ssh = Get-WindowsCapability -Online -Name 'OpenSSH.Client*' -ErrorAction SilentlyContinue
if ($ssh -and $ssh.State -eq 'Installed') {
    Write-Host 'OpenSSH client                 : Installed'
} else {
    Write-Warning 'OpenSSH client is not installed.'
}

$task = Get-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates' -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "Scheduled tool-update task     : Present ($($task.State))"
} else {
    Write-Warning 'Scheduled tool-update task is missing.'
}

Write-Host ''
Write-Host 'GUI applications:'
$gui = @{
    'DBeaver' = @('C:\Program Files\DBeaver\dbeaver.exe','C:\Program Files\DBeaver\dbeaver-ce.exe');
    'PyCharm' = @('C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe');
    'Chrome' = @('C:\Program Files\Google\Chrome\Application\chrome.exe','C:\Program Files (x86)\Google\Chrome\Application\chrome.exe');
    'Firefox' = @('C:\Program Files\Mozilla Firefox\firefox.exe','C:\Program Files (x86)\Mozilla Firefox\firefox.exe')
}
foreach ($k in $gui.Keys) {
    $found = $gui[$k] | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($found) { Write-Host ("  {0,-10} OK  {1}" -f $k,$found) } else { Write-Warning "$k not found in expected path." }
}
