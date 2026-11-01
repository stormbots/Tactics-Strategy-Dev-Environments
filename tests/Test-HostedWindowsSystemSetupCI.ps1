$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Hosted runtime preparation requires a disposable GitHub runner.' }
# The full Node-conflict regression normally replaces the hosted image's
# untracked Node 22 MSI. It now runs on another VM. Prepare this VM's baseline
# with a real, explicitly requested Chocolatey Node 24 installation instead.
# Never relax production's refusal to replace an untracked runtime, remove its
# registry/package records, force an MSI or synthesize an installed baseline.
$choco = 'C:\ProgramData\chocolatey\bin\choco.exe'
& $choco install nodejs-lts --version 24.21.0 -y --no-progress
if ($LASTEXITCODE -notin @(0,3010)) { throw 'Hosted fixture Node 24 preparation failed.' }
$rows = @(& $choco list --limit-output)
if ($LASTEXITCODE -ne 0 -or -not ($rows -match '^nodejs-lts\|24\.21\.0$')) { throw 'Hosted fixture Node 24 package record missing.' }
$actual = & 'C:\Program Files\nodejs\node.exe' --version
if ($LASTEXITCODE -ne 0 -or $actual -ne 'v24.21.0') { throw 'Hosted fixture Node 24 runtime mismatch.' }
Write-Host 'SKYVIEW_CI_NODE24_BASELINE_READY'
. (Join-Path $PSScriptRoot 'Test-WindowsSystemSetupCI.ps1')
