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
foreach ($name in @('Assert-TrustedItem','Protect-LegacyMaintenanceParent')) {
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
try {
    Set-FixtureAcl $fixture $legacy
    Protect-LegacyMaintenanceParent
    Assert-TrustedItem $fixture
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($file)) -ne $bytes) { throw 'Migration changed baseline bytes.' }
    if ((Get-Acl -LiteralPath $file).Sddl -ne $fileAcl.Sddl) { throw 'Migration changed private child permissions.' }
    $after = (Get-Acl -LiteralPath $fixture).Sddl
    Protect-LegacyMaintenanceParent
    if ((Get-Acl -LiteralPath $fixture).Sddl -ne $after) { throw 'Migration is not idempotent.' }
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
