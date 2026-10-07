[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$ErrorActionPreference = 'Stop'
function Event($Type,$Key,$Message) { Write-Host ("SKYVIEW_EVENT|{0}|{1}|{2}" -f $Type,$Key,($Message -replace '[\r\n]',' ')) }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run profile configuration without elevation.' }
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
Event progress 82 'Configuring your workspace and editor'
New-Item -ItemType Directory -Path 'C:\Development' -Force | Out-Null
git config --global init.defaultBranch main
if ($LASTEXITCODE) { throw 'Could not configure Git.' }
git config --global fetch.prune true
git config --global pull.ff only
$explorer = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'
if (-not (Test-Path $explorer)) { New-Item $explorer -Force | Out-Null }
Set-ItemProperty $explorer -Name HideFileExt -Type DWord -Value 0
$codium = 'C:\Program Files\VSCodium\bin\codium.cmd'
if (-not (Test-Path $codium)) { $codium = (Get-Command codium -ErrorAction Stop).Source }
foreach ($ext in (Get-Content (Join-Path $PSScriptRoot 'extensions.txt') | Where-Object { $_ -and $_ -notmatch '^\s*#' })) {
    Event phase extensions "Installing editor extension $ext"
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $codium --install-extension $ext --force 2>&1 | ForEach-Object { Write-Host $_ }
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previous }
    if ($code -ne 0) { throw "Editor extension $ext failed with exit code $code." }
}
$settingsDir = Join-Path $env:APPDATA 'VSCodium\User'
New-Item -ItemType Directory $settingsDir -Force | Out-Null
$settings = Join-Path $settingsDir 'settings.json'
if (-not (Test-Path $settings)) { Copy-Item (Join-Path $PSScriptRoot 'settings.json') $settings }
else { Event warning settings 'Your existing editor settings were preserved. Baseline defaults are available in the installed package.' }
$config = 'C:\ProgramData\SkyviewRobotics\repositories.csv'
if (-not (Test-Path $config)) { $config = Join-Path $PSScriptRoot 'repositories.csv' }
& (Join-Path $PSScriptRoot 'Setup-SkyviewRepositories.ps1') -Config $config
Event progress 94 'Your workspace is configured'
