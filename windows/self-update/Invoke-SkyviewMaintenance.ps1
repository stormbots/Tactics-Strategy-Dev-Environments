# Fixed schema-1 launcher outside Program Files. Run only as scheduled SYSTEM.
$ErrorActionPreference = 'Stop'
$root = 'C:\ProgramData\SkyviewRobotics\SelfUpdate'
if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne 'S-1-5-18') { throw 'SYSTEM maintenance required.' }
# This file and all ancestors are administrator-controlled. Reuse no environment
# paths, PATH executables, caller script arguments or generation path fragments.
function Assert-LauncherItem([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Untrusted engine link.' }
    $acl = Get-Acl -LiteralPath $Path
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544')) { throw 'Untrusted engine owner.' }
    $write = [Security.AccessControl.FileSystemRights]::Write -bor [Security.AccessControl.FileSystemRights]::Delete -bor [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor [Security.AccessControl.FileSystemRights]::ChangePermissions -bor [Security.AccessControl.FileSystemRights]::TakeOwnership
    foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq 'Allow' -and ($rule.FileSystemRights -band $write) -and $rule.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544')) { throw 'Untrusted engine writers.' }
    }
}
foreach ($path in @('C:\ProgramData\SkyviewRobotics',$root,(Join-Path $root 'active.json'),(Join-Path $root 'engines'),(Join-Path $root 'runs'))) { Assert-LauncherItem $path }
$receipt = Get-Content -LiteralPath (Join-Path $root 'active.json') -Raw | ConvertFrom-Json
if ($receipt.schemaVersion -ne 1 -or $receipt.generation -notmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' -or $receipt.version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid active engine receipt.' }
$engine = Join-Path (Join-Path $root 'engines') $receipt.generation
Assert-LauncherItem $engine
$run = Join-Path (Join-Path $root 'runs') ([guid]::NewGuid().ToString())
$security = New-Object Security.AccessControl.DirectorySecurity
$security.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)')
[IO.Directory]::CreateDirectory($run,$security) | Out-Null
$code = 1
try {
    foreach ($name in @('sde-update-trust.exe','version.json')) {
        $source = Join-Path $engine $name
        Assert-LauncherItem $source
        Copy-Item -LiteralPath $source -Destination (Join-Path $run $name)
    }
    $snapshot = Get-Content -LiteralPath (Join-Path $run 'version.json') -Raw | ConvertFrom-Json
    if ($snapshot.version -ne $receipt.version -or $snapshot.schemaVersion -ne 1) { throw 'Engine snapshot version mismatch.' }
    & (Join-Path $run 'sde-update-trust.exe') maintain-windows
    $code = $LASTEXITCODE
} finally {
    # A crash leaves this private snapshot for mentor diagnostics. No deletion of
    # another invocation or installer/recovery material, even when work is busy.
    foreach ($name in @('sde-update-trust.exe','version.json')) {
        $path = Join-Path $run $name
        if (Test-Path $path) { Remove-Item -LiteralPath $path }
    }
    [IO.Directory]::Delete($run)
}
exit $code
