param([string]$Version)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Coordination.ps1')
try {
Invoke-SkyviewCoordinated -Mutation -Action {
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Node24.ps1')
Install-SkyviewNode24 -Version $Version
Write-Host 'Node.js remains on the approved 24.x family and nodejs-lts is pinned.'

}
} catch {
    if ($_.Exception.Message -eq 'SKYVIEW_DEFERRED') {
        Write-Host 'SKYVIEW_EVENT|warning|deferred|SDE is busy. Maintenance will retry at its next scheduled invocation.'
        exit 75
    }
    throw
}
