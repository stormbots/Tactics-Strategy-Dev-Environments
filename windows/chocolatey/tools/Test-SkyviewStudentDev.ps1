param([switch]$CheckUpdates)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Coordination.ps1')
try {
Invoke-SkyviewCoordinated -ReadOnly -Action {
& (Join-Path $PSScriptRoot 'Validate-SkyviewEnvironment.ps1') -CheckUpdates:$CheckUpdates
exit $LASTEXITCODE

}
} catch {
    if ($_.Exception.Message -eq 'SKYVIEW_DEFERRED') {
        Write-Host 'SKYVIEW_EVENT|warning|deferred|SDE is busy. Maintenance will retry at its next scheduled invocation.'
        exit 75
    }
    throw
}
