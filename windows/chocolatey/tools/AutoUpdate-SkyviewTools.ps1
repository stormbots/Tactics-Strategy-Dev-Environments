$ErrorActionPreference = 'Stop'

$LogDir = 'C:\ProgramData\SkyviewRobotics\Logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$Log = Join-Path $LogDir ("AutoUpdate-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))
Start-Transcript -Path $Log -Force | Out-Null

try {
    $Chocolatey = 'C:\ProgramData\chocolatey\bin\choco.exe'
    if (-not (Test-Path $Chocolatey)) { throw 'Chocolatey executable not found.' }

    # Node.js is intentionally excluded. It is pinned and mentor-controlled.
    $Packages = @(
        'chocolatey',
        'git',
        'gh',
        'vscodium',
        'dbeaver',
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

    Write-Host 'Automatic Skyview tool update complete.'
}
finally {
    Stop-Transcript | Out-Null
}
