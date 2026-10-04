# Skyview Robotics Windows 11 development workstation bootstrap
# Run from an elevated Windows PowerShell prompt while logged in to the shared local-admin account.

$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script with Run as administrator.'
}

if (-not (Get-Command choco.exe -ErrorAction SilentlyContinue)) {
    Write-Host 'Installing Chocolatey...'
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}

$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$local = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = "$local;https://community.chocolatey.org/api/v2/"

Write-Host 'Installing Skyview student development package...'
choco install skyview-student-dev --version 1.0.0 --source="$source" -y --no-progress
$exit = $LASTEXITCODE
if ($exit -notin @(0,1605,1614,1641,3010)) { throw "Chocolatey returned exit code $exit" }

Write-Host ''
Write-Host 'Installation complete.'
Write-Host 'Sign out/in or reboot if VSCodium/Node commands are not immediately visible.'
Write-Host 'Then run:'
Write-Host '  powershell -ExecutionPolicy Bypass -File C:\ProgramData\SkyviewRobotics\Test-SkyviewStudentDev.ps1'
