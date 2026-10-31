# Installed application/NSIS integration. Synthetic journal on disposable CI only.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub runner required.' }
Import-Module "$PSHOME\Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1" -ErrorAction Stop
$root = 'C:\ProgramData\SkyviewRoboticsCoordination'
$journal = Join-Path $root 'transaction.json'
$app = 'C:\Program Files\Skyview Dev Setup\skyview-dev-setup.exe'
$package = (Resolve-Path 'dist/Skyview-Dev-Setup-Windows-x64.exe').Path
$metadata = @('recovery-incident.json','recovery-binding.json','recovery-acknowledgment.json','recovery-context.json')
foreach ($name in @('transaction.json','recovery-archive','recovery-disposition.json') + $metadata) {
    if (Test-Path -LiteralPath (Join-Path $root $name)) { throw 'Expected a clean disposable bootstrap fixture.' }
}
$original = [Text.Encoding]::UTF8.GetBytes('{"schema":1,"kind":"system","token":"synthetic-bootstrap-ci-only"}')
$security = New-Object Security.AccessControl.FileSecurity
$security.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)')
$file = New-Object IO.FileStream($journal,[IO.FileMode]::CreateNew,[Security.AccessControl.FileSystemRights]::Write,[IO.FileShare]::None,4096,[IO.FileOptions]::WriteThrough,$security)
try { $file.Write($original,0,$original.Length); $file.Flush($true) } finally { $file.Dispose() }
function Assert-OriginalJournal {
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($journal)) -cne [Convert]::ToBase64String($original)) { throw 'Bootstrap changed original evidence.' }
    foreach ($rule in (Get-Acl -LiteralPath $journal).GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544')) { throw 'Bootstrap exposed private evidence.' }
    }
}
function Invoke-InstalledInitialization {
    $process = Start-Process -FilePath $app -ArgumentList '--coordination-init' -Wait -PassThru
    try { if ($process.ExitCode -ne 0) { throw 'Installed recovery initialization failed.' } } finally { $process.Dispose() }
}
$operation = $null
$succeeded = $false
try {
    # A package hook invoked by a live updater must not deadlock/fail its own
    # supervisor, change gate identity, or publish live work as an interruption.
    $operation = [IO.File]::Open((Join-Path $root 'operations.gate'), 'Open', 'Read', 'None')
    Invoke-InstalledInitialization
    foreach ($name in $metadata) {
        if (Test-Path -LiteralPath (Join-Path $root $name)) { throw 'Live transaction was published as an interruption.' }
    }
    $stillHeld = $false
    try { $probe = [IO.File]::Open((Join-Path $root 'operations.gate'), 'Open', 'Read', 'None'); $probe.Dispose() }
    catch [IO.IOException] { if (($_.Exception.HResult -band 0xffff) -ne 32) { throw }; $stillHeld = $true }
    if (-not $stillHeld) { throw 'Bootstrap replaced the held operation gate.' }
    $operation.Dispose(); $operation = $null
    Assert-OriginalJournal
    # Exercise the actual installed NSIS post-install hook with retained legacy
    # evidence, not just the checkout library or a fixture-only implementation.
    $process = Start-Process -FilePath $package -ArgumentList '/S','/UPDATE' -Wait -PassThru
    try { if ($process.ExitCode -notin @(0,3010)) { throw 'Legacy-evidence NSIS installation failed.' } } finally { $process.Dispose() }
    Assert-OriginalJournal
    $incident = Get-Content (Join-Path $root 'recovery-incident.json') -Raw | ConvertFrom-Json
    if ($incident.schema -ne 1 -or @($incident.PSObject.Properties).Count -ne 2 -or
        $incident.incidentId -cnotmatch '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$') { throw 'Invalid sanitized bootstrap incident.' }
    $context = [IO.File]::ReadAllBytes((Join-Path $root 'recovery-context.json'))
    $intent = '{"schema":1,"incidentId":"' + $incident.incidentId + '"}'
    [IO.File]::WriteAllText((Join-Path $root 'recovery-acknowledgment.json'), $intent, (New-Object Text.UTF8Encoding($false)))
    Invoke-InstalledInitialization
    Assert-OriginalJournal
    $again = Get-Content (Join-Path $root 'recovery-incident.json') -Raw | ConvertFrom-Json
    if ($again.incidentId -cne $incident.incidentId -or [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $root 'recovery-context.json'))) -cne [Convert]::ToBase64String($context)) { throw 'Repeated bootstrap reset incident or restart provenance.' }
    if ([IO.File]::ReadAllText((Join-Path $root 'recovery-acknowledgment.json')) -cne $intent) { throw 'Repeated bootstrap lost submitted intent.' }
    foreach ($name in @('recovery-archive','recovery-disposition.json')) {
        if (Test-Path -LiteralPath (Join-Path $root $name)) { throw 'Bootstrap acknowledged or retired an interruption.' }
    }
    $status = & ./coordination/target/release/sde-coordination.exe status
    if ($LASTEXITCODE -ne 0 -or $status -cne '"interrupted"') { throw 'Bootstrap released the legacy execution gate.' }
    . 'C:\Program Files\Skyview Dev Setup\backend\windows\chocolatey\tools\Coordination.ps1'
    $blocked = $false
    try { Invoke-SkyviewCoordinated -Mutation -Action { throw 'Interrupted action must never run.' } }
    catch { if ($_.Exception.Message -notlike '*interrupted*mentor*') { throw }; $blocked = $true }
    if (-not $blocked) { throw 'Bootstrap released the installed script execution gate.' }
    Assert-OriginalJournal
    if (Test-Path 'C:\ProgramData\SkyviewRobotics\Update-SkyviewTools.ps1') { throw 'Bootstrap applied a tool baseline.' }
    if (Get-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates' -ErrorAction SilentlyContinue) { throw 'Bootstrap scheduled tool maintenance.' }
    $succeeded = $true
} finally {
    if ($operation) { $operation.Dispose() }
    # Clean only a successful, byte-verified synthetic case. Keep failed CI
    # evidence rather than deleting an unexpected record or partial publication.
    if ($succeeded) {
        Assert-OriginalJournal
        foreach ($name in @('transaction.json') + $metadata) { Remove-Item -LiteralPath (Join-Path $root $name) -Force }
    }
}
Write-Output 'SDE_RECOVERY_WINDOWS_INSTALLED_BOOTSTRAP_OK'
