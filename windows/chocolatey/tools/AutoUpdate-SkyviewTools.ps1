$ErrorActionPreference = 'Stop'

$LogDir = 'C:\ProgramData\SkyviewRobotics\Logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$Log = Join-Path $LogDir ("AutoUpdate-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))
Start-Transcript -Path $Log -Force | Out-Null

try {
    & (Join-Path $PSScriptRoot 'Update-SkyviewTools.ps1')

}
finally {
    Stop-Transcript | Out-Null
}
