param([switch]$CheckUpdates)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$ErrorActionPreference = 'Continue'
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$script:Failures = 0
function Result($Status,$Message) {
    if ($Status -eq 'FAIL') { $script:Failures++ }
    Write-Host ("SKYVIEW_EVENT|validation|{0}|{1}" -f $Status,($Message -replace '[\r\n]',' '))
    Write-Host "$Status $Message"
}
function Check($Condition,$Message) { if ($Condition) { Result PASS $Message } else { Result FAIL $Message } }
foreach ($check in @(
    @{Name='Git'; Command='git'; Args=@('--version')},
    @{Name='GitHub CLI'; Command='gh'; Args=@('--version')},
    @{Name='Node.js'; Command='node'; Args=@('--version'); Family='^v24\.'},
    @{Name='npm'; Command='npm'; Args=@('--version')},
    @{Name='Python'; Command='python'; Args=@('--version'); Family='^Python 3\.14\.'},
    @{Name='pip'; Command='python'; Args=@('-m','pip','--version')},
    @{Name='VSCodium'; Command='codium'; Args=@('--version')},
    @{Name='PowerShell 7'; Command='pwsh'; Args=@('--version')},
    @{Name='OpenSSH'; Command='ssh'; Args=@('-V')},
    @{Name='7-Zip'; Command='7z'; Args=@('i')}
)) {
    $cmd = Get-Command $check.Command -ErrorAction SilentlyContinue
    if (-not $cmd) { Result FAIL "$($check.Name): not installed"; continue }
    $out = @(& $cmd.Source @($check.Args) 2>&1)
    $code = $LASTEXITCODE
    $version = [string]($out | Where-Object { [string]$_ -notmatch '^\s*$' } | Select-Object -First 1)
    if ($code -ne 0 -or ($check.Family -and $version -notmatch $check.Family)) {
        Result FAIL "$($check.Name): expected runtime family or usable command; detected $version"
    } else { Result PASS "$($check.Name): $version" }
}
foreach ($entry in @(
    @{Name='DBeaver'; Paths=@('C:\Program Files\DBeaver\dbeaver.exe','C:\Program Files\DBeaver\dbeaver-ce.exe')},
    @{Name='PyCharm'; Paths=@('C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe')},
    @{Name='Chrome'; Paths=@('C:\Program Files\Google\Chrome\Application\chrome.exe','C:\Program Files (x86)\Google\Chrome\Application\chrome.exe')},
    @{Name='Firefox'; Paths=@('C:\Program Files\Mozilla Firefox\firefox.exe','C:\Program Files (x86)\Mozilla Firefox\firefox.exe')}
)) {
    $found = @($entry.Paths | ForEach-Object { Get-Item $_ -ErrorAction SilentlyContinue } | Select-Object -First 1)
    if ($found.Count) { Result PASS "$($entry.Name): $($found[0].VersionInfo.ProductVersion)" }
    else { Result FAIL "$($entry.Name): not installed" }
}
Check (Test-Path 'C:\Development') 'Development folder'
foreach ($setting in @(@{Key='init.defaultBranch';Value='main'},@{Key='fetch.prune';Value='true'},@{Key='pull.ff';Value='only'})) {
    $value = git config --global --get $setting.Key 2>$null
    Check ($value -eq $setting.Value) "Git default $($setting.Key) = $($setting.Value)"
}
$gitName = git config --global --get user.name 2>$null
$gitEmail = git config --global --get user.email 2>$null
if ($gitName -and $gitEmail) { Result INFO 'Git identity: configured locally' }
else { Result INFO 'Git identity: not configured (optional)' }
if (Get-Command gh -ErrorAction SilentlyContinue) {
    & gh auth status *> $null
    if ($LASTEXITCODE -eq 0) { Result INFO 'GitHub authentication: configured locally' }
    else { Result INFO 'GitHub authentication: not configured (optional)' }
}
$task = Get-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates' -ErrorAction SilentlyContinue
Check ($null -ne $task -and $task.State -ne 'Disabled') 'Weekly maintenance enabled'
$longPaths = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
Check ($longPaths -eq 1) 'Windows long paths enabled'
$devMode = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock' -Name AllowDevelopmentWithoutDevLicense -ErrorAction SilentlyContinue).AllowDevelopmentWithoutDevLicense
Check ($devMode -eq 1) 'Windows developer mode enabled'
$fileExt = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced' -Name HideFileExt -ErrorAction SilentlyContinue).HideFileExt
Check ($fileExt -eq 0) 'File extensions visible'
Check (Test-Path (Join-Path $env:APPDATA 'VSCodium\User\settings.json')) 'VSCodium settings present'
if (Get-Command codium -ErrorAction SilentlyContinue) {
    $extensions = @(& codium --list-extensions 2>$null)
    foreach ($ext in (Get-Content (Join-Path $PSScriptRoot 'extensions.txt') | Where-Object { $_ -and $_ -notmatch '^\s*#' })) {
        Check ($extensions -contains $ext) "Editor extension: $ext"
    }
}
$config = 'C:\ProgramData\SkyviewRobotics\repositories.csv'
if (Test-Path $config) {
    foreach ($repo in (Import-Csv $config)) {
        if (-not $repo.Url) { continue }
        $folder = if ($repo.Folder) { $repo.Folder } else { $repo.Name }
        Check (Test-Path (Join-Path "C:\Development\$folder" '.git')) "Configured repository: $($repo.Name)"
    }
}
if ($CheckUpdates -and (Get-Command choco -ErrorAction SilentlyContinue)) {
    $managed = @('git','gh','nodejs-lts','python314','vscodium','dbeaver','pycharm','firefox','powershell-core','7zip')
    $rows = & choco outdated --limit-output --ignore-unfound 2>$null
    if ($LASTEXITCODE -notin @(0,2)) { Result WARNING 'Available updates could not be checked. Your installed tool checks are still valid.' }
    foreach ($row in $rows) {
        $parts = $row -split '\|'
        if ($parts.Count -ge 3 -and $parts[0] -in $managed) {
            if ($parts[0] -eq 'nodejs-lts' -and $parts[2] -notmatch '^24\.') { continue }
            Write-Host "SKYVIEW_EVENT|update|available|$($parts[0]): $($parts[1]) to $($parts[2])"
        }
    }
}
Write-Host "SKYVIEW_EVENT|summary|$script:Failures|Validation completed with $script:Failures failed checks"
if ($script:Failures -gt 0) { exit 1 }
exit 0
