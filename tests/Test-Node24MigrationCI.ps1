$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:SDE_RUN_NATIVE_PACKAGES -ne '1') { throw 'Runtime installation tests require an explicitly authorized disposable GitHub runner.' }
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
# The hosted runner executes CI inside its preinstalled PowerShell Core. Adopt
# that exact runtime through the upstream package's normal (non-forced) install
# path, which verifies/reuses an existing equal-or-newer installation. Do not
# replace CI's own shell or enter the package's unbounded ancestor walk during
# this unrelated Node/SDE regression. No scripts, checksums or package DB are
# bypassed; the real backend below still installs/configures the metapackage.
$core = 'C:\Program Files\PowerShell\7\pwsh.exe'
if (Test-Path $core) {
    $version = (Get-Command $core).Version
    if ($version.Major -ne 7) { throw 'Expected the hosted runner PowerShell 7 fixture.' }
    $packageVersion = '{0}.{1}.{2}' -f $version.Major,$version.Minor,$version.Build
    & $choco install powershell-core --version $packageVersion -y --no-progress
    if ($LASTEXITCODE -notin @(0,3010)) { throw 'Could not adopt the existing CI PowerShell runtime through Chocolatey.' }
    if ((Get-Command $core).Version -ne $version) { throw 'CI shell adoption unexpectedly replaced the runtime.' }
    Write-Host 'SKYVIEW_CI_POWERSHELL_REUSE_OK'
}
# Continue through the real system setup so dependency/configuration failures
# beyond the previously failing MSI are covered before shipping another patch.
for ($attempt = 1; $attempt -le 2; $attempt++) {
    try {
        & (Join-Path $PSScriptRoot '../windows/Install-SkyviewStudentDev.ps1') -SystemOnly
        break
    }
    catch {
        # The public feed occasionally returns a gateway error after installing
        # dependencies. Retry that external failure once, using the real backend;
        # application/MSI/assertion errors still fail immediately.
        $feedFailure = Get-Content 'C:\ProgramData\chocolatey\logs\chocolatey.log' -Tail 80 |
            Select-String -Pattern 'Failed to fetch.*(50[234]|Gateway Timeout)'
        if ($attempt -eq 2 -or $_.Exception.Message -ne 'Chocolatey returned exit code 1' -or -not $feedFailure) { throw }
        if (Get-Process choco,msiexec -ErrorAction SilentlyContinue) { throw 'Package processes remain; fixture recovery is unsafe.' }
        $journal = 'C:\ProgramData\SkyviewRoboticsCoordination\transaction.json'
        if (Test-Path $journal) {
            # This fixture observed the completed Chocolatey failure and contains
            # no other actors. Clear only the SDE record, never package locks.
            $gate = [IO.File]::Open('C:\ProgramData\SkyviewRoboticsCoordination\operations.gate','Open','Read','None')
            try { Remove-Item $journal -Force } finally { $gate.Dispose() }
        }
        Write-Host 'Retrying the real system backend once after a temporary Chocolatey feed gateway failure.'
        Start-Sleep -Seconds 15
    }
}
if (-not (Test-Path 'C:\ProgramData\SkyviewRobotics\Node24.ps1')) { throw 'Maintenance migration helper was not deployed.' }
if (-not (Get-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates' -ErrorAction SilentlyContinue)) { throw 'Weekly maintenance task was not registered.' }
if (-not (Test-Path 'C:\Development')) { throw 'Development workspace was not created.' }
& (Join-Path $PSScriptRoot 'Test-MaintenanceCI.ps1') -CheckInstalledTask
$coordinator = Join-Path $PSScriptRoot '../coordination/target/release/sde-coordination.exe'
$status = & $coordinator status | ConvertFrom-Json
if ($status -ne 'idle') { throw "Provisioned maintenance is not safely coordinated: $status" }
Write-Host 'SKYVIEW_SYSTEM_SETUP_OK'
