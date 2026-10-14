# Real NTFS permission regressions; disposable Windows runner only, no packages.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable CI runner required.' }
$fixture = Join-Path 'C:\ProgramData' ('SdeLegacyAcl-' + [guid]::NewGuid().ToString('N'))
$private = 'O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'
$normal = $private + '(A;;FRFX;;;BU)'
$legacy = 'O:BAG:BAD:AI(A;OICIID;FA;;;SY)(A;OICIID;FA;;;BA)(A;OICIIOID;GA;;;CO)(A;OICIID;0x1200a9;;;BU)(A;CIID;DCLCRPCR;;;BU)'
function Set-FixtureAcl([string]$Path,[string]$Sddl) {
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetSecurityDescriptorSddlForm($Sddl)
    Set-Acl -LiteralPath $Path -AclObject $acl
}
# Load the actual production functions without executing the packaging entry
# point. Substitute only its fixed path to isolate adversarial NTFS fixtures.
$source = Join-Path $PSScriptRoot '../windows/self-update/Bootstrap-SkyviewSelfUpdate.ps1'
$tokens = $null; $errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Bootstrap parse failed.' }
foreach ($name in @('Assert-TrustedItem','Open-LegacyDirectoryGuard','Open-LegacyLogGuard','Assert-LegacyLogsDirectory','Protect-LegacyMaintenanceParent')) {
    $node = $ast.Find({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name },$true)
    if (-not $node) { throw 'Expected production migration function missing.' }
    Invoke-Expression ($node.Extent.Text.Replace('C:\ProgramData\SkyviewRobotics',$fixture))
}
New-Item -ItemType Directory -Path $fixture | Out-Null
Set-FixtureAcl $fixture $normal
$file = Join-Path $fixture 'protected-baseline.ps1'
Set-Content -LiteralPath $file '# unchanged baseline sentinel'
$fileAcl = New-Object Security.AccessControl.FileSecurity
$fileAcl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)')
Set-Acl -LiteralPath $file -AclObject $fileAcl
$bytes = [Convert]::ToBase64String([IO.File]::ReadAllBytes($file))
$logs = Join-Path $fixture 'Logs'
$log = Join-Path $logs 'AutoUpdate-20261014-051807.log'
function Reset-LegacyLogs {
    Set-FixtureAcl $fixture $normal
    if (Test-Path -LiteralPath $logs) { Remove-Item -LiteralPath $logs -Recurse -Force }
    Set-FixtureAcl $fixture $legacy
    New-Item -ItemType Directory -Path $logs | Out-Null
    $acl = Get-Acl -LiteralPath $logs
    $acl.SetOwner((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))
    Set-Acl -LiteralPath $logs -AclObject $acl
    $grant = @($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | Where-Object {
        $_.IdentityReference.Value -eq 'S-1-5-32-545' -and $_.IsInherited -and ($_.FileSystemRights -band [Security.AccessControl.FileSystemRights]::Write)
    })
    if ($grant.Count -ne 1 -or $grant[0].InheritanceFlags -ne [Security.AccessControl.InheritanceFlags]::ContainerInherit) { throw 'Reported inherited Logs grant was not reproduced.' }
    Set-Content -LiteralPath $log 'Preserved legacy diagnostic evidence; not authenticated history.'
    Set-Acl -LiteralPath $log -AclObject $fileAcl
}
function Assert-LogsRejection {
    $parentBefore = (Get-Acl -LiteralPath $fixture).Sddl
    $logsBefore = (Get-Acl -LiteralPath $logs).Sddl
    $rejected = $false
    try { Protect-LegacyMaintenanceParent } catch { $rejected = $true }
    if (-not $rejected) { throw 'Unsafe Logs fixture was accepted.' }
    if ((Get-Acl -LiteralPath $fixture).Sddl -ne $parentBefore -or (Get-Acl -LiteralPath $logs).Sddl -ne $logsBefore) { throw 'Rejected layout was modified before validation completed.' }
}
try {
    Set-FixtureAcl $fixture $legacy
    $guard = Open-LegacyDirectoryGuard $fixture
    try {
        $probe = [SdeLegacyDirectoryNative]::CreateFile($fixture,2,7,[IntPtr]::Zero,3,0x02000000,[IntPtr]::Zero)
        $errorCode = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        try { if (-not $probe.IsInvalid -or $errorCode -ne 32) { throw "Directory guard did not block concurrent write-data handles: invalid=$($probe.IsInvalid), error=$errorCode." } }
        finally { $probe.Dispose() }
    } finally { $guard.Dispose() }
    $childBefore = (Get-Acl -LiteralPath $file).Sddl
    Protect-LegacyMaintenanceParent
    Assert-TrustedItem $fixture
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($file)) -ne $bytes) { throw 'Migration changed baseline bytes.' }
    if ((Get-Acl -LiteralPath $file).Sddl -ne $childBefore) { throw 'Migration changed private child permissions.' }
    $after = (Get-Acl -LiteralPath $fixture).Sddl
    Protect-LegacyMaintenanceParent
    if ((Get-Acl -LiteralPath $fixture).Sddl -ne $after) { throw 'Migration is not idempotent.' }

    # Exact October 14 fixture: only Logs has an untrusted effective write;
    # existing file bytes and owner already meet the original trust contract.
    Reset-LegacyLogs
    $reproduced = $false
    try { Assert-TrustedItem $logs } catch { $reproduced = $_.ToString() -like '*Untrusted maintenance writers*' }
    if (-not $reproduced) { throw 'Original bootstrap rejection was not reproduced.' }
    Assert-TrustedItem $log
    $logBytes = [Convert]::ToBase64String([IO.File]::ReadAllBytes($log))
    $logAcl = (Get-Acl -LiteralPath $log).Sddl
    $baselineAcl = (Get-Acl -LiteralPath $file).Sddl
    Protect-LegacyMaintenanceParent
    foreach ($entry in @($fixture,$logs,$log,$file)) { Assert-TrustedItem $entry }
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($log)) -ne $logBytes -or (Get-Acl -LiteralPath $log).Sddl -ne $logAcl) { throw 'Log evidence or private ACL changed.' }
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($file)) -ne $bytes -or (Get-Acl -LiteralPath $file).Sddl -ne $baselineAcl) { throw 'Baseline bytes or private permissions changed.' }
    $logsAfter = (Get-Acl -LiteralPath $logs).Sddl
    Protect-LegacyMaintenanceParent
    if ((Get-Acl -LiteralPath $logs).Sddl -ne $logsAfter) { throw 'Logs migration is not idempotent.' }
    # Files which inherit read/full access but no write grant remain supported.
    Reset-LegacyLogs
    $inheritedLog = Join-Path $logs 'AutoUpdate-20261014-051808.log'
    Set-Content -LiteralPath $inheritedLog 'Second diagnostic log'
    Assert-TrustedItem $inheritedLog
    $inheritedBytes = [Convert]::ToBase64String([IO.File]::ReadAllBytes($inheritedLog))
    Protect-LegacyMaintenanceParent
    Assert-TrustedItem $inheritedLog
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($inheritedLog)) -ne $inheritedBytes) { throw 'Inherited log bytes changed.' }
    Reset-LegacyLogs
    Remove-Item -LiteralPath $log
    Protect-LegacyMaintenanceParent
    Assert-TrustedItem $logs

    # A stopped migration after Logs protection but before parent protection
    # can be retried through the existing protected-descendant path.
    Reset-LegacyLogs
    Set-FixtureAcl $logs ($private + '(A;OICI;FRFX;;;BU)')
    Protect-LegacyMaintenanceParent
    Assert-TrustedItem $fixture
    Assert-TrustedItem $log

    Reset-LegacyLogs
    $guard = Open-LegacyDirectoryGuard $logs
    $logGuard = Open-LegacyLogGuard $log
    try {
        foreach ($entry in @($logs,$log)) {
            foreach ($access in @(2,0x10000)) {
                $probe = [SdeLegacyDirectoryNative]::CreateFile($entry,$access,7,[IntPtr]::Zero,3,0x02200000,[IntPtr]::Zero)
                $errorCode = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
                try { if (-not $probe.IsInvalid -or $errorCode -ne 32) { throw 'Logs guard did not block writer/rename/delete handles.' } }
                finally { $probe.Dispose() }
            }
        }
    } finally { $logGuard.Dispose(); $guard.Dispose() }
    # Exercise the production commit boundary: introduce an extra entry after
    # the inventory, or fail after Logs hardening. Use a cmdlet shim solely for
    # deterministic fault injection; production code and native pinning are real.
    $script:injectLogsAddition = $true
    function Set-Acl {
        param([string]$LiteralPath,$AclObject)
        if ($LiteralPath -eq $logs -and $script:injectLogsAddition) {
            $script:injectLogsAddition = $false
            $extraLog = Join-Path $logs 'AutoUpdate-20261014-051809.log'
            [IO.File]::WriteAllText($extraLog,'Concurrent addition must not be silently accepted.')
            Microsoft.PowerShell.Security\Set-Acl -LiteralPath $extraLog -AclObject $fileAcl
        }
        Microsoft.PowerShell.Security\Set-Acl -LiteralPath $LiteralPath -AclObject $AclObject
    }
    $parentBefore = (Get-Acl -LiteralPath $fixture).Sddl
    $rejected = $false
    try { Protect-LegacyMaintenanceParent } catch { $rejected = $_.ToString() -like '*entries changed during migration*' }
    Remove-Item Function:\Set-Acl
    if (-not $rejected -or (Get-Acl -LiteralPath $fixture).Sddl -ne $parentBefore) { throw 'Concurrent Logs addition was accepted or parent committed before validation.' }
    # The directory was protected before detecting the added entry. Retrying
    # revalidates both already protected files instead of fabricating success.
    Protect-LegacyMaintenanceParent
    Assert-TrustedItem $fixture
    Reset-LegacyLogs
    # An already open writer blocks migration before either directory changes.
    $writer = [IO.File]::Open($log,'Open','Write','ReadWrite')
    try { Assert-LogsRejection } finally { $writer.Dispose() }
    Protect-LegacyMaintenanceParent

    Reset-LegacyLogs
    $unsafeLogAcl = New-Object Security.AccessControl.FileSecurity
    $unsafeLogAcl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FW;;;BU)')
    Set-Acl -LiteralPath $log -AclObject $unsafeLogAcl
    Assert-LogsRejection
    Reset-LegacyLogs
    Rename-Item -LiteralPath $log -NewName 'policy.json'
    Assert-LogsRejection
    Reset-LegacyLogs
    $alias = Join-Path $fixture 'log-alias'
    New-Item -ItemType HardLink -Path $alias -Target $log | Out-Null
    try { Assert-LogsRejection } finally { Remove-Item -LiteralPath $alias }
    Reset-LegacyLogs
    New-Item -ItemType Directory -Path (Join-Path $logs 'nested') | Out-Null
    Assert-LogsRejection
    Reset-LegacyLogs
    Remove-Item -LiteralPath $log
    New-Item -ItemType Junction -Path $log -Target $env:WINDIR | Out-Null
    try { Assert-LogsRejection } finally { [IO.Directory]::Delete($log) }
    Reset-LegacyLogs
    foreach ($unsafe in @($normal + '(A;;FW;;;BU)', $normal + '(A;CI;0x1301bf;;;BU)', $normal + '(A;OICI;FW;;;BU)')) {
        Set-FixtureAcl $logs $unsafe
        Assert-LogsRejection
    }
    Reset-LegacyLogs
    $ownerAcl = Get-Acl -LiteralPath $logs
    $ownerAcl.SetOwner([Security.Principal.WindowsIdentity]::GetCurrent().User)
    Set-Acl -LiteralPath $logs -AclObject $ownerAcl
    Assert-LogsRejection
    Reset-LegacyLogs
    $ownerAcl = Get-Acl -LiteralPath $log
    $ownerAcl.SetOwner([Security.Principal.WindowsIdentity]::GetCurrent().User)
    Set-Acl -LiteralPath $log -AclObject $ownerAcl
    Assert-LogsRejection
    Reset-LegacyLogs
    # Another writable child must prevent correction of even supported Logs.
    $unsafeFileAcl = New-Object Security.AccessControl.FileSecurity
    $unsafeFileAcl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FW;;;BU)')
    Set-Acl -LiteralPath $file -AclObject $unsafeFileAcl
    Assert-LogsRejection
    Set-Acl -LiteralPath $file -AclObject $fileAcl
    Set-FixtureAcl $fixture $normal
    Remove-Item -LiteralPath $logs -Recurse -Force
    Write-Output 'SDE_LEGACY_LOGS_ACL_OK'
    foreach ($unsafe in @(($normal + '(A;;0x1301bf;;;BU)'), ($normal + '(A;OICI;0x116;;;BU)'), ($normal + '(A;;0x116;;;WD)'), ($legacy + '(D;;FR;;;BU)'))) {
        Set-FixtureAcl $fixture $unsafe
        $before = (Get-Acl -LiteralPath $fixture).Sddl
        $rejected = $false
        try { Protect-LegacyMaintenanceParent } catch { $rejected = $true }
        if (-not $rejected -or (Get-Acl -LiteralPath $fixture).Sddl -ne $before) { throw 'Unsafe grant was accepted or modified.' }
    }
    Set-FixtureAcl $fixture $legacy
    $unsafeFileAcl = New-Object Security.AccessControl.FileSecurity
    $unsafeFileAcl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FW;;;BU)')
    Set-Acl -LiteralPath $file -AclObject $unsafeFileAcl
    $before = (Get-Acl -LiteralPath $fixture).Sddl
    $rejected = $false
    try { Protect-LegacyMaintenanceParent } catch { $rejected = $true }
    if (-not $rejected -or (Get-Acl -LiteralPath $fixture).Sddl -ne $before) { throw 'Writable child was laundered by migration.' }
    Set-Acl -LiteralPath $file -AclObject $fileAcl
    $link = Join-Path $fixture 'linked-child'
    New-Item -ItemType Junction -Path $link -Target $env:WINDIR | Out-Null
    $rejected = $false
    try { Protect-LegacyMaintenanceParent } catch { $rejected = $true }
    if (-not $rejected) { throw 'Linked child was accepted.' }
    [IO.Directory]::Delete($link)
    Write-Output 'SDE_LEGACY_PARENT_ACL_OK'
} finally {
    $link = Join-Path $fixture 'linked-child'
    if (Test-Path -LiteralPath $link) { [IO.Directory]::Delete($link) }
    Set-FixtureAcl $fixture $normal
    Remove-Item -LiteralPath $fixture -Recurse -Force
}
