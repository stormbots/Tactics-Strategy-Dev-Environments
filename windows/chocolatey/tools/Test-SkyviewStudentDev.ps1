param([switch]$CheckUpdates)
& (Join-Path $PSScriptRoot 'Validate-SkyviewEnvironment.ps1') -CheckUpdates:$CheckUpdates
exit $LASTEXITCODE
