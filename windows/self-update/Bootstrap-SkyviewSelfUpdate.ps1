# Packaging hook only: no tool provisioning, package actions or maintenance launch.
# An intermediate NSIS process can inherit PowerShell 7's incompatible module
# paths. Load only native system modules, including ACL and scheduled-task APIs.
$env:PSModulePath = 'C:\Windows\System32\WindowsPowerShell\v1.0\Modules'
$ErrorActionPreference = 'Stop'
$root = 'C:\ProgramData\SkyviewRobotics\SelfUpdate'
function Assert-TrustedItem([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Untrusted maintenance link.' }
    $acl = Get-Acl -LiteralPath $Path
    $owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
    if ($owner -notin @('S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')) { throw 'Untrusted maintenance owner.' }
    $write = [Security.AccessControl.FileSystemRights]::Write -bor [Security.AccessControl.FileSystemRights]::Delete -bor [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor [Security.AccessControl.FileSystemRights]::ChangePermissions -bor [Security.AccessControl.FileSystemRights]::TakeOwnership
    foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq 'Allow' -and -not ($rule.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -and ($rule.FileSystemRights -band $write) -and $rule.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')) { throw 'Untrusted maintenance writers.' }
    }
}
function New-ProtectedDirectory([string]$Path,[switch]$Readable) {
    if (Test-Path -LiteralPath $Path) { Assert-TrustedItem $Path; return }
    # Create with private security atomically, without a writable inheritance gap.
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $sddl = 'O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'
    if ($Readable) { $sddl += '(A;OICI;FRFX;;;BU)' }
    $acl.SetSecurityDescriptorSddlForm($sddl)
    [IO.Directory]::CreateDirectory($Path,$acl) | Out-Null
    Assert-TrustedItem $Path
}
function Write-AtomicReceipt([string]$Path,$Value) {
    $temporary = Join-Path (Split-Path $Path -Parent) ([guid]::NewGuid().ToString() + '.tmp')
    $bytes = [Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Compress))
    $file = New-Object IO.FileStream($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None,4096,[IO.FileOptions]::WriteThrough)
    try { $file.Write($bytes,0,$bytes.Length); $file.Flush($true) } finally { $file.Dispose() }
    # Windows PowerShell 5.1 converts $null to an empty string for .NET string
    # parameters. Replace needs a genuine null backup filename, not an empty path.
    if (Test-Path -LiteralPath $Path) { Assert-TrustedItem $Path; [IO.File]::Replace($temporary,$Path,[NullString]::Value) }
    else { [IO.File]::Move($temporary,$Path) }
}
try {
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Administrator installation required.' }
$app = (Get-Item (Join-Path $PSScriptRoot '../../../skyview-dev-setup.exe')).FullName
$install = Split-Path $app -Parent
if (-not $install.StartsWith('C:\Program Files\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Expected machine application installation.' }
foreach ($path in @($install,$app,$PSScriptRoot,(Join-Path $PSScriptRoot 'sde-update-trust.exe'))) { Assert-TrustedItem $path }
$version = (Get-Item $app).VersionInfo.ProductVersion
if ($version -match '^\d+\.\d+\.\d+\.0$') { $version = $version.Substring(0,$version.Length-2) }
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid application version.' }
# Parent directories must already be machine-protected or freshly created here.
New-ProtectedDirectory 'C:\ProgramData\SkyviewRobotics' -Readable
New-ProtectedDirectory $root -Readable
foreach ($name in @('engines','runs','staging','logs')) { New-ProtectedDirectory (Join-Path $root $name) }
$generation = [guid]::NewGuid().ToString()
$engine = Join-Path (Join-Path $root 'engines') $generation
New-ProtectedDirectory $engine
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'sde-update-trust.exe') -Destination $engine
Write-AtomicReceipt (Join-Path $engine 'version.json') @{schemaVersion=1;version=$version}
foreach ($name in @('Invoke-SkyviewMaintenance.ps1','Publish-SkyviewStatus.ps1')) {
    $target = Join-Path $root $name
    # Fixed schema-1 launchers are immutable while a task may be executing them.
    # Future incompatible launcher changes need an explicit mentor migration.
    if (-not (Test-Path $target)) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $target }
    Assert-TrustedItem $target
}
if (-not (Test-Path (Join-Path $root 'policy.json'))) {
    # Production rollout needs owner UAT and #41 pause/recovery controls first.
    Write-AtomicReceipt (Join-Path $root 'policy.json') @{schemaVersion=1;paused=$true}
}
# Publish only the non-secret pause boolean with read-only student access.
$policyPath = Join-Path $root 'policy.json'
Assert-TrustedItem $policyPath
$policyAcl = New-Object Security.AccessControl.FileSecurity
$policyAcl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FR;;;BU)')
Set-Acl -LiteralPath $policyPath -AclObject $policyAcl
$active = Join-Path $root 'active.json'
if (Test-Path $active) {
    Assert-TrustedItem $active
    $previous = Get-Content -LiteralPath $active -Raw | ConvertFrom-Json
    Write-AtomicReceipt (Join-Path $root 'previous-engine.json') $previous
}
Write-AtomicReceipt $active @{schemaVersion=1;version=$version;generation=$generation}
# Only migrate an existing, provisioned task. Preserve its triggers, settings,
# enabled state, principal and standard-user read access; never start it here.
$baseline = 'C:\ProgramData\SkyviewRobotics\Update-SkyviewTools.ps1'
$taskName = 'Skyview Robotics - Dev Tool Updates'
if (Test-Path $baseline) {
    Assert-TrustedItem $baseline
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task -and (Get-Content $baseline -Raw) -match '# SDE_COORDINATION_V1') {
        if ($task.Principal.UserId -notin @('SYSTEM','S-1-5-18','NT AUTHORITY\SYSTEM')) { throw 'Unexpected maintenance task principal.' }
        $launcher = Join-Path $root 'Invoke-SkyviewMaintenance.ps1'
        $action = New-ScheduledTaskAction -Execute 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$launcher`""
        Set-ScheduledTask -TaskName $taskName -Action $action | Out-Null
        . (Join-Path $install 'backend/windows/chocolatey/tools/ScheduledMaintenance.ps1')
        Set-SkyviewMaintenanceReadAccess -TaskName $taskName
    }
}
# Receipt publication is the commit point; retain current and previous engines.
# Active invocations use private copies, never a live engine directory.
$keep = @($generation)
if ($previous -and $previous.generation -match '^[0-9a-f-]{36}$') { $keep += $previous.generation }
Get-ChildItem -LiteralPath (Join-Path $root 'engines') -Directory | ForEach-Object {
    if ($_.Name -match '^[0-9a-f-]{36}$' -and $_.Name -notin $keep) {
        Assert-TrustedItem $_.FullName
        foreach ($name in @('sde-update-trust.exe','version.json')) { Remove-Item -LiteralPath (Join-Path $_.FullName $name) }
        [IO.Directory]::Delete($_.FullName)
    }
}

} catch {
    # Packaging-only diagnostic: no signing credentials or package output here.
    $diagnostic = Join-Path $PSScriptRoot 'bootstrap-error.log'
    if (Test-Path -LiteralPath $diagnostic) { Assert-TrustedItem $diagnostic }
    [IO.File]::WriteAllText($diagnostic, ($_.ToString() + [Environment]::NewLine + 'native64=' + [Environment]::Is64BitProcess))
    throw
}
