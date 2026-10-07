param([string]$Version)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Node24.ps1')
Install-SkyviewNode24 -Version $Version
Write-Host 'Node.js remains on the approved 24.x family and nodejs-lts is pinned.'
