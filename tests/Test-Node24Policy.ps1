$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/Node24.ps1')
function Assert-Plan($Packages, $Versions, $Expected) {
    $plan = Get-SkyviewNode24Plan $Packages $Versions
    if (($plan -join ',') -ne $Expected) { throw "Unexpected migration plan: $plan" }
}
Assert-Plan @{} @() ''
Assert-Plan @{'nodejs-lts'='24.21.0'} @('24.21.0') ''
Assert-Plan @{'nodejs'='26.1.0';'nodejs.install'='26.1.0'} @('26.1.0') 'nodejs,nodejs.install'
Assert-Plan @{'nodejs.install'='24.21.0'} @('24.21.0') 'nodejs.install'
Assert-Plan @{'nodejs-lts'='26.1.0'} @('26.1.0') 'nodejs-lts'
foreach ($case in @(
    @{Packages=@{}; Versions=@('26.1.0')},
    @{Packages=@{'nodejs.install'='26.1.0'}; Versions=@('26.2.0')}
)) {
    $rejected = $false
    try { Get-SkyviewNode24Plan $case.Packages $case.Versions | Out-Null }
    catch { $rejected = $true }
    if (-not $rejected) { throw 'An unmanaged/mismatched runtime was accepted for removal.' }
}
Write-Host 'Seven read-only Node 24 migration policy cases passed.'
