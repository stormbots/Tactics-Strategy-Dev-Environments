$ErrorActionPreference = 'Stop'
$Chocolatey = 'C:\ProgramData\chocolatey\bin\choco.exe'
if (-not (Test-Path $Chocolatey)) { throw 'Chocolatey executable not found.' }

$Packages = @(
    'git',
    'gh',
    'vscodium',
    'dbeaver',
    'pycharm',
    'firefox',
    'powershell-core',
    '7zip'
)

foreach ($Package in $Packages) {
    Write-Host "Updating $Package..."
    & $Chocolatey upgrade $Package -y --no-progress
    if ($LASTEXITCODE -notin @(0, 1605, 1614, 1641, 3010)) {
        Write-Warning "$Package update returned exit code $LASTEXITCODE"
    }
}

Write-Host 'Non-runtime development tools updated. Node.js remains pinned.'
Write-Host 'Google Chrome is intentionally excluded and uses its native Google Update mechanism.'
