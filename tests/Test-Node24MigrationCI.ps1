$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Runtime installation tests are restricted to disposable GitHub runners.' }
$choco = 'C:\ProgramData\chocolatey\bin\choco.exe'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/Node24.ps1')
# Simulate the reported real MSI/channel conflict, rather than a fake package.
$packages = @(& $choco list --limit-output)
foreach ($id in @('nodejs', 'nodejs.install', 'nodejs-lts')) {
    if ($packages -match ('^' + [regex]::Escape($id) + '\|')) {
        Invoke-SkyviewNodeChocolatey $choco @('uninstall', $id, '-y', '--no-progress')
    }
}
Invoke-SkyviewNodeChocolatey $choco @('install', 'nodejs', '--version', '26.1.0', '-y', '--no-progress')
$node = 'C:\Program Files\nodejs\node.exe'
if ((& $node --version) -ne 'v26.1.0') { throw 'The conflicting runtime fixture was not installed.' }
Install-SkyviewNode24 -Version '24.21.0'
# A retry must reuse the resulting runtime without another removal/reinstall.
Install-SkyviewNode24 -Version '24.21.0'
$packages = @(& $choco list --limit-output)
if ($packages -match '^nodejs(\.install)?\|') { throw 'The unbounded Node package channel remains installed.' }
if (-not ($packages -match '^nodejs-lts\|24\.21\.0$')) { throw 'Approved Node package record missing.' }
$pins = @(& $choco pin list --limit-output)
if (-not ($pins -match '^nodejs-lts\|')) { throw 'Approved Node package is not pinned.' }
Write-Host 'SKYVIEW_NODE_MIGRATION_OK'
. (Join-Path $PSScriptRoot 'Test-WindowsSystemSetupCI.ps1')
