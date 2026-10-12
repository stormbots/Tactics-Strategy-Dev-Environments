# Embedded in the authenticated worker; accepts no caller paths or commands.
$ErrorActionPreference = 'Stop'
if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne 'S-1-5-18') { throw 'SYSTEM maintenance required.' }
. (Join-Path $PSScriptRoot 'MaintenanceCoordination.ps1')
$snapshot = Join-Path $PSScriptRoot 'applied-baseline'
function Assert-AppliedFile([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Invalid applied maintenance file.' }
    $acl = Get-Acl -LiteralPath $Path
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544')) { throw 'Untrusted applied maintenance owner.' }
    $write = [Security.AccessControl.FileSystemRights]::Write -bor [Security.AccessControl.FileSystemRights]::Delete -bor [Security.AccessControl.FileSystemRights]::ChangePermissions -bor [Security.AccessControl.FileSystemRights]::TakeOwnership
    foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq 'Allow' -and ($rule.FileSystemRights -band $write) -and $rule.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544')) { throw 'Untrusted applied maintenance writers.' }
    }
}
$names = @('Update-SkyviewTools.ps1','Update-Node24.ps1','Node24.ps1','Coordination.ps1')
try {
    Invoke-SkyviewCoordinated -Mutation -Action {
        # Acquire the shared operation lease BEFORE reading deployed scripts.
        # A concurrent mentor Repair cannot mix their policy generations.
        Assert-SkyviewProtectedPath 'C:\ProgramData\SkyviewRobotics'
        $security = New-Object Security.AccessControl.DirectorySecurity
        $security.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)')
        [IO.Directory]::CreateDirectory($snapshot,$security) | Out-Null
        foreach ($name in $names) {
            $source = Join-Path 'C:\ProgramData\SkyviewRobotics' $name
            Assert-AppliedFile $source
            Copy-Item -LiteralPath $source -Destination (Join-Path $snapshot $name)
        }
        # The private journal/token authorizes this child to reuse our held
        # transaction. Wait through its completion; never terminate packages.
        & 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $snapshot 'Update-SkyviewTools.ps1')
        if ($LASTEXITCODE -ne 0) { throw "Applied maintenance returned exit code $LASTEXITCODE; mentor review required." }
    }
} catch {
    if ($_.Exception.Message -eq 'SKYVIEW_DEFERRED') { exit 75 }
    throw
} finally {
    if (Test-Path -LiteralPath $snapshot) {
        foreach ($name in $names) {
            $path = Join-Path $snapshot $name
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
        }
        [IO.Directory]::Delete($snapshot)
    }
}
exit 0
