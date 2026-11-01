# SDE_COORDINATION_V1
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Coordination.ps1')
try {
Invoke-SkyviewCoordinated -Mutation -EntryPoint $PSCommandPath -Action {
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$ErrorActionPreference = 'Stop'
$Chocolatey = 'C:\ProgramData\chocolatey\bin\choco.exe'
if (-not (Test-Path $Chocolatey)) { throw 'Chocolatey executable not found.' }

$Packages = @(
    'git',
    'gh',
    'python314',
    'vscodium',
    'dbeaver',
    'pycharm',
    'firefox',
    'powershell-core',
    '7zip'
)

foreach ($Package in $Packages) {
    Write-Host "SKYVIEW_EVENT|phase|$Package|Updating $Package"
    Write-Host "Updating $Package..."
    & $Chocolatey upgrade $Package -y --no-progress
    if ($LASTEXITCODE -notin @(0, 1605, 1614, 1641, 3010)) {
        throw "$Package update returned exit code $LASTEXITCODE"
    }
}

& (Join-Path $PSScriptRoot 'Update-Node24.ps1')
Write-Host 'Development tools updated.'
Write-Host 'Node.js remains pinned and mentor-controlled.'
Write-Host 'Python remains on the python314 package family and receives Python 3.14.x updates.'
Write-Host 'Google Chrome is intentionally excluded and uses its native Google Update mechanism.'

}
} catch {
    if ($_.Exception.Message -eq 'SKYVIEW_DEFERRED') {
        Write-Host 'SKYVIEW_EVENT|warning|deferred|SDE is busy. Maintenance will retry at its next scheduled invocation.'
        exit 75
    }
    throw
}
