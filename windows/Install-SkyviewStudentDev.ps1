# Skyview Robotics Windows 11 development workstation bootstrap
# Run from an elevated Windows PowerShell prompt while logged in to the shared local-admin account.

$ErrorActionPreference = 'Stop'

$PackageVersion = '1.0.1'
$ExpectedSetupRoot = 'C:\SkyviewRobotics\DevSetup'
$ChocolateyLog = 'C:\ProgramData\chocolatey\logs\chocolatey.log'

function Write-Phase {
    param(
        [int]$Number,
        [int]$Total,
        [string]$Message
    )

    Write-Host ''
    Write-Host ("[{0}/{1}] {2}" -f $Number, $Total, $Message) -ForegroundColor Cyan
}

function Invoke-ChocolateyWithHeartbeat {
    param(
        [string[]]$Arguments,
        [int]$HeartbeatSeconds = 20
    )

    $chocoPath = (Get-Command choco.exe -ErrorAction Stop).Source

    Write-Host 'Chocolatey may be quiet while resolving package metadata and dependencies.'
    Write-Host ("A status heartbeat will appear every {0} seconds while Chocolatey is still running." -f $HeartbeatSeconds)
    Write-Host 'Do not close this window while the heartbeat continues.' -ForegroundColor Yellow

    $process = Start-Process -FilePath $chocoPath -ArgumentList $Arguments -NoNewWindow -PassThru
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $nextHeartbeat = $HeartbeatSeconds

    while (-not $process.HasExited) {
        Start-Sleep -Seconds 1
        $process.Refresh()

        if ($stopwatch.Elapsed.TotalSeconds -ge $nextHeartbeat) {
            $elapsed = $stopwatch.Elapsed.ToString('hh\:mm\:ss')
            Write-Host ("  [still working] Chocolatey process is active - elapsed {0}" -f $elapsed) -ForegroundColor DarkGray
            $nextHeartbeat += $HeartbeatSeconds
        }
    }

    $process.WaitForExit()
    $stopwatch.Stop()
    $elapsed = $stopwatch.Elapsed.ToString('hh\:mm\:ss')
    Write-Host ("Chocolatey process finished after {0}." -f $elapsed) -ForegroundColor DarkGray

    return $process.ExitCode
}

function Test-ChromeInstalled {
    return (
        (Test-Path 'C:\Program Files\Google\Chrome\Application\chrome.exe') -or
        (Test-Path 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe')
    )
}

function Install-GoogleChrome {
    if (Test-ChromeInstalled) {
        Write-Host 'Google Chrome is already installed.' -ForegroundColor Green
        return
    }

    $msi = Join-Path $env:TEMP 'googlechromestandaloneenterprise64.msi'
    $uri = 'https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi'

    try {
        Write-Host 'Downloading Google Chrome from Google...'
        Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $msi

        Write-Host 'Verifying Google digital signature...'
        $signature = Get-AuthenticodeSignature -FilePath $msi
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Google') {
            throw "Chrome installer signature validation failed. Status: $($signature.Status)"
        }

        Write-Host 'Installing Google Chrome...'
        $process = Start-Process -FilePath 'msiexec.exe' -ArgumentList @('/i', "`"$msi`"", '/qn', '/norestart') -Wait -PassThru
        if ($process.ExitCode -notin @(0, 1641, 3010)) {
            throw "Chrome installer returned exit code $($process.ExitCode)"
        }

        if (-not (Test-ChromeInstalled)) {
            throw 'Chrome installation completed but chrome.exe was not found in an expected location.'
        }

        Write-Host 'Google Chrome installed successfully.' -ForegroundColor Green
    }
    finally {
        Remove-Item $msi -Force -ErrorAction SilentlyContinue
    }
}

Write-Host '============================================================'
Write-Host ' Skyview Robotics Student Development Environment'
Write-Host " Windows package version $PackageVersion"
Write-Host '============================================================'
Write-Host ''
Write-Host 'This installer may take 10-20 minutes on a fresh laptop.'
Write-Host 'Live Chocolatey output will be shown when available, with periodic status heartbeats during quiet periods.'

Write-Phase 1 5 'Running preflight checks...'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from Windows PowerShell using Run as administrator.'
}
Write-Host 'Administrator privileges: OK' -ForegroundColor Green

$actualSetupRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
if (-not $actualSetupRoot.Equals($ExpectedSetupRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Extract the complete development package to $ExpectedSetupRoot, then run the installer from that folder. Current folder: $actualSetupRoot"
}
Write-Host "Deployment location: $ExpectedSetupRoot" -ForegroundColor Green

Write-Phase 2 5 'Checking Chocolatey package manager...'
if (-not (Get-Command choco.exe -ErrorAction SilentlyContinue)) {
    Write-Host 'Chocolatey is not installed. Installing it now...'
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
} else {
    Write-Host 'Chocolatey is already installed.' -ForegroundColor Green
}

$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$local = $PSScriptRoot
$source = "$local;https://community.chocolatey.org/api/v2/"

Write-Phase 3 5 'Installing core development software...'
Write-Host 'This is the longest phase.'
Write-Host 'Already-installed packages will be skipped or reused.'

$chocoArgs = @(
    'install',
    'skyview-student-dev',
    '--version', $PackageVersion,
    "--source=$source",
    '-y'
)
$exit = Invoke-ChocolateyWithHeartbeat -Arguments $chocoArgs -HeartbeatSeconds 20

if ($exit -notin @(0,1605,1614,1641,3010)) {
    Write-Host ''
    Write-Host 'Core development package installation failed.' -ForegroundColor Red
    Write-Host "Chocolatey exit code: $exit"
    Write-Host "Chocolatey log: $ChocolateyLog"
    Write-Host 'It is safe to correct the reported problem and rerun this installer.'
    throw "Chocolatey returned exit code $exit"
}
Write-Host 'Core development software installation completed.' -ForegroundColor Green

Write-Phase 4 5 'Installing and verifying Google Chrome...'
try {
    Install-GoogleChrome
}
catch {
    Write-Warning "Google Chrome could not be installed automatically: $($_.Exception.Message)"
    Write-Warning 'The core development environment will remain installed. Chrome can be installed manually and the installer rerun later.'
}

Write-Phase 5 5 'Finishing installation...'
Write-Host 'Installation workflow complete.' -ForegroundColor Green
Write-Host ''
Write-Host 'If VSCodium or Node commands are not immediately visible, sign out/in or reboot.'
Write-Host 'Then validate the workstation with:'
Write-Host '  powershell -ExecutionPolicy Bypass -File C:\ProgramData\SkyviewRobotics\Test-SkyviewStudentDev.ps1'
Write-Host ''
Write-Host 'This installer is designed to be rerun safely after a partial or interrupted installation.'
