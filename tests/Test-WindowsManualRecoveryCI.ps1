# ONLY a disposable GitHub runner, before real tool provisioning. Synthetic
# no-package scripts exercise the installed release binary, not a checkout stub.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable CI required.' }
Import-Module "$PSHOME\Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1" -ErrorAction Stop
$root = 'C:\ProgramData\SkyviewRoboticsCoordination'
$installed = 'C:\Program Files\Skyview Dev Setup\backend\windows\chocolatey\tools'
. (Join-Path $installed 'Coordination.ps1')
if (Test-Path (Join-Path $root 'transaction.json')) { throw 'Expected clean synthetic fixture.' }
if (Test-Path (Join-Path $root 'recovery-archive')) { throw 'Unexpected recovery history.' }
# Use the exact read-only diagnostic compiled into this head. No package process
# is killed and no timeout is treated as inactivity; a busy fixture fails closed.
$deadline = [DateTime]::UtcNow.AddMinutes(15)
do {
    $facts = & 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -File (Join-Path $PSScriptRoot '../coordination/src/inspection/windows.ps1') | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $facts.activity -eq 'unknown' -or $facts.health -eq 'incomplete') { throw 'Native fixture inactivity unavailable or package state incomplete.' }
    if ($facts.activity -eq 'inactive') { break }
    if ($facts.activity -ne 'active' -or [DateTime]::UtcNow -ge $deadline) { throw 'Native fixture package activity did not become inactive.' }
    Start-Sleep -Seconds 10
} while ($true)
$fixture = Join-Path 'C:\ProgramData' ('SdeManualRecovery-' + [guid]::NewGuid().ToString('N'))
$security = New-Object Security.AccessControl.DirectorySecurity
$security.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)')
[IO.Directory]::CreateDirectory($fixture,$security) | Out-Null
Copy-Item (Join-Path $installed 'Coordination.ps1') $fixture
$script = Join-Path $fixture 'Update-SkyviewTools.ps1'
$ready = Join-Path $fixture 'child-ran'
@'
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Coordination.ps1')
Invoke-SkyviewCoordinated -Mutation -EntryPoint $PSCommandPath -Action {
    if (-not $env:SKYVIEW_TRANSACTION_TOKEN -or $env:SDE_UNTRUSTED_MANUAL_ENV) { throw 'Missing native nesting or contaminated environment.' }
    $held = $false
    try { $gate = [IO.File]::Open('C:\ProgramData\SkyviewRoboticsCoordination\operations.gate','Open','Read','Read'); $gate.Dispose() }
    catch [IO.IOException] { if (($_.Exception.HResult -band 0xffff) -ne 32) { throw }; $held = $true }
    if (-not $held) { throw 'Lost native operation lease.' }
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'child-ran'),'native nesting proved')
    Write-Host 'SDE_WINDOWS_MANUAL_STREAM_OK'
}
'@ | Set-Content -LiteralPath $script -Encoding UTF8
$capability = Invoke-SkyviewNativeMaintenanceProcess -Arguments @('--coordination-init') -Capture
if ($capability.ExitCode -ne 0 -or $capability.Output.Trim() -cne 'SDE_WINDOWS_MAINTENANCE_SUPERVISOR_V1') { throw 'Installed capability unavailable.' }
$invalid = Invoke-SkyviewNativeMaintenanceProcess -Arguments @('--supervise-windows-maintenance',$script,'-Skip')
if ($invalid.ExitCode -ne 76 -or (Test-Path $ready)) { throw 'Extra options accepted.' }
# Actual standard-user process, not an administrator's interpretation of ACLs.
$user = 'SdeManual' + [guid]::NewGuid().ToString('N').Substring(0,7)
$public = Join-Path 'C:\Users\Public' ('SdeManualProbe-' + [guid]::NewGuid().ToString('N'))
$created = $false
try {
    New-Item -ItemType Directory $public | Out-Null
    $bridge = Join-Path $public 'student.ps1'
    @'
$ErrorActionPreference = 'Stop'
. 'C:\Program Files\Skyview Dev Setup\backend\windows\chocolatey\tools\Coordination.ps1'
$result = Invoke-SkyviewNativeMaintenanceProcess -Arguments @('--supervise-windows-maintenance','C:\ProgramData\not-present\Update-SkyviewTools.ps1')
if ($result.ExitCode -ne 76) { throw 'Standard token was accepted.' }
Write-Output 'SDE_WINDOWS_MANUAL_STUDENT_DENIED_OK'
'@ | Set-Content $bridge -Encoding UTF8
    $password = ConvertTo-SecureString ('Ci!' + [guid]::NewGuid().ToString('N') + 'aA7') -AsPlainText -Force
    $credential = New-Object Management.Automation.PSCredential("$env:COMPUTERNAME\$user",$password)
    New-LocalUser -Name $user -Password $password -AccountNeverExpires -PasswordNeverExpires | Out-Null
    $created = $true
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user
    Start-Service seclogon
    $stdout = Join-Path $public 'stdout.txt'; $stderr = Join-Path $public 'stderr.txt'
    $student = Start-Process 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$bridge`"" -Credential $credential -LoadUserProfile -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    [void]$student.Handle
    $student.WaitForExit()
    if ($student.ExitCode -ne 0 -or -not (Select-String $stdout -Pattern '^SDE_WINDOWS_MANUAL_STUDENT_DENIED_OK\s*$')) { throw 'Standard-user denial not demonstrated.' }
    $student.Dispose()
} finally {
    if ($created) { Remove-LocalUser $user }
    # Only this validated fixed-prefix disposable directory; no owner logs.
    if (Test-Path $public) { Remove-Item -LiteralPath $public -Recurse -Force }
}
if (Test-Path (Join-Path $root 'transaction.json')) { throw 'Rejected invocation created a journal.' }
# Effective student write on an otherwise protected script must be rejected.
$originalAcl = Get-Acl $script
$unsafeAcl = Get-Acl $script
$unsafeAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule('Users','Write','Allow')))
try {
    Set-Acl $script $unsafeAcl
    $invalid = Invoke-SkyviewNativeMaintenanceProcess -Arguments @('--supervise-windows-maintenance',$script)
    if ($invalid.ExitCode -ne 76 -or (Test-Path $ready)) { throw 'Untrusted script was accepted.' }
} finally { Set-Acl $script $originalAcl }
$env:SDE_UNTRUSTED_MANUAL_ENV = 'must-not-reach-child'
try {
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $script
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $ready)) { throw 'Installed outer maintenance did not complete.' }
} finally { Remove-Item Env:SDE_UNTRUSTED_MANUAL_ENV }
Remove-Item $ready
if (Test-Path (Join-Path $root 'transaction.json')) { throw 'Known-completed journal was retained.' }
$node = Join-Path $fixture 'Update-Node24.ps1'
$nodeBody = [IO.File]::ReadAllText($script).Replace(
    'Invoke-SkyviewCoordinated -Mutation -EntryPoint $PSCommandPath -Action {',
    'Invoke-SkyviewCoordinated -Mutation -EntryPoint $PSCommandPath -EntryArguments @(''-Version'',$Version) -Action {')
$nodeBody = $nodeBody.Replace("'native nesting proved'", '$Version')
[IO.File]::WriteAllText($node,('param([string]$Version)' + [Environment]::NewLine + $nodeBody),(New-Object Text.UTF8Encoding($false)))
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $node -Version '24.21.0'
if ($LASTEXITCODE -ne 0 -or [IO.File]::ReadAllText($ready) -cne '24.21.0') { throw 'Version data was not preserved across supervision.' }
Remove-Item $ready
$setup = Join-Path $fixture 'Install-SkyviewStudentDev.ps1'
$setupBody = [IO.File]::ReadAllText($script).Replace(
    'Invoke-SkyviewCoordinated -Mutation -EntryPoint $PSCommandPath -Action {',
    '$entryArguments = @(); if ($SystemOnly) { $entryArguments += ''-SystemOnly'' }; if ($Repair) { $entryArguments += ''-Repair'' }; Invoke-SkyviewCoordinated -Mutation -EntryPoint $PSCommandPath -EntryArguments $entryArguments -Action {')
$setupBody = $setupBody.Replace("'native nesting proved'", '(@{systemOnly=[bool]$SystemOnly;repair=[bool]$Repair;profile=$env:USERPROFILE;roaming=$env:APPDATA;local=$env:LOCALAPPDATA} | ConvertTo-Json -Compress)')
[IO.File]::WriteAllText($setup,('param([switch]$SystemOnly,[switch]$Repair)' + [Environment]::NewLine + $setupBody),(New-Object Text.UTF8Encoding($false)))
$expectedProfile = [Environment]::GetFolderPath('UserProfile')
$expectedRoaming = [Environment]::GetFolderPath('ApplicationData')
$expectedLocal = [Environment]::GetFolderPath('LocalApplicationData')
foreach ($case in @(@{args=@();systemOnly=$false;repair=$false},@{args=@('-Repair');systemOnly=$false;repair=$true},@{args=@('-SystemOnly');systemOnly=$true;repair=$false},@{args=@('-SystemOnly','-Repair');systemOnly=$true;repair=$true})) {
    $originalProfile = $env:USERPROFILE; $originalRoaming = $env:APPDATA; $originalLocal = $env:LOCALAPPDATA
    try {
        $env:USERPROFILE='C:\untrusted-profile'; $env:APPDATA='C:\untrusted-roaming'; $env:LOCALAPPDATA='C:\untrusted-local'
        $arguments = $case.args
        & 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $setup @arguments
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $ready)) { throw 'Installed Install/Repair did not complete.' }
    } finally { $env:USERPROFILE=$originalProfile; $env:APPDATA=$originalRoaming; $env:LOCALAPPDATA=$originalLocal }
    $observed = Get-Content $ready -Raw | ConvertFrom-Json
    if ($observed.systemOnly -ne $case.systemOnly -or $observed.repair -ne $case.repair) { throw 'Install/Repair switches were not preserved.' }
    if ($case.systemOnly) {
        if ($observed.profile -cne 'C:\Windows\System32\config\systemprofile') { throw 'SystemOnly changed profile policy.' }
    } elseif ($observed.profile -cne $expectedProfile -or $observed.roaming -cne $expectedRoaming -or $observed.local -cne $expectedLocal) { throw 'Manual setup lost native current-account known folders.' }
    if (Test-Path (Join-Path $root 'transaction.json')) { throw 'Known-completed setup retained a journal.' }
    Remove-Item $ready
}
$env:SKYVIEW_TRANSACTION_TOKEN = 'forged-ci-only'
$previousErrorPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $script 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0 -or (Test-Path $ready)) { throw 'Forged nesting was accepted.' }
} finally { $ErrorActionPreference = $previousErrorPreference; Remove-Item Env:SKYVIEW_TRANSACTION_TOKEN }
# Create an isolated legacy incident with the production journal's private ACL.
$journal = Join-Path $root 'transaction.json'
$original = '{"schema":1,"id":"windows-manual-ci-only","kind":"system"}'
$fileSecurity = New-Object Security.AccessControl.FileSecurity
$fileSecurity.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)')
$file = New-Object IO.FileStream($journal,[IO.FileMode]::CreateNew,[Security.AccessControl.FileSystemRights]::Write,[IO.FileShare]::None,4096,[IO.FileOptions]::WriteThrough,$fileSecurity)
try { $bytes=[Text.Encoding]::UTF8.GetBytes($original);$file.Write($bytes,0,$bytes.Length);$file.Flush($true) } finally {$file.Dispose()}
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $setup -SystemOnly -Repair
if ($LASTEXITCODE -ne 75 -or (Test-Path $ready) -or [IO.File]::ReadAllText($journal) -cne $original) { throw 'Unacknowledged incident was released.' }
$incident = Get-Content (Join-Path $root 'recovery-incident.json') -Raw | ConvertFrom-Json
$id = [guid]::ParseExact($incident.incidentId,'D').ToString()
if ($id -cne $incident.incidentId) { throw 'Invalid incident identity.' }
$contextPath = Join-Path $root 'recovery-context.json'
$context = Get-Content $contextPath -Raw | ConvertFrom-Json
if ($context.bootKey -notmatch '^windows-session-start:(\d+):(\d+):(\d+):(\d+)$') { throw 'Native restart provenance unavailable.' }
# Simulate previous provenance only in this synthetic CI incident. Never reboot
# the machine, clear a package lock, or create an application override flag.
$context.bootKey = 'windows-session-start:' + ((1..4 | ForEach-Object { ([long]$Matches[$_] + 1).ToString([Globalization.CultureInfo]::InvariantCulture) }) -join ':')
$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($contextPath,($context | ConvertTo-Json -Compress),$utf8)
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $setup -SystemOnly -Repair
if ($LASTEXITCODE -ne 75 -or (Test-Path $ready) -or [IO.File]::ReadAllText($journal) -cne $original) { throw 'Restart replaced consent.' }
[IO.File]::WriteAllText((Join-Path $root 'recovery-acknowledgment.json'),($incident | ConvertTo-Json -Compress),$utf8)
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $setup -SystemOnly -Repair
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $ready) -or (Test-Path $journal)) { throw 'Acknowledged maintenance continuation failed.' }
$archive = Join-Path $root 'recovery-archive'
$expected = @("$id.journal","$id.receipt.json","$id.retired-journal")
if (@(Get-ChildItem $archive).Count -ne 3) { throw 'Unexpected archive contents.' }
foreach ($suffix in @('journal','retired-journal')) {
    if ([IO.File]::ReadAllText((Join-Path $archive "$id.$suffix")) -cne $original) { throw 'Original evidence changed.' }
}
if (-not (Test-Path (Join-Path $archive "$id.receipt.json"))) { throw 'Missing private receipt.' }
# Cleanup only verified synthetic history, under the operation gate; no active
# journal is removed. Any preceding failure leaves evidence for diagnosis.
$gate = [IO.File]::Open((Join-Path $root 'operations.gate'),'Open','Read','None')
try {
    if (Test-Path $journal) { throw 'Unexpected active transaction during cleanup.' }
    foreach ($name in $expected) { Remove-Item -LiteralPath (Join-Path $archive $name) }
    [IO.Directory]::Delete($archive)
    foreach ($name in @('recovery-incident.json','recovery-binding.json','recovery-context.json','recovery-acknowledgment.json','recovery-disposition.json')) {
        $path = Join-Path $root $name
        if (Test-Path $path) { Remove-Item -LiteralPath $path }
    }
} finally { $gate.Dispose() }
Write-Output 'SDE_RECOVERY_WINDOWS_MANUAL_MAINTENANCE_OK'
Write-Output 'SDE_RECOVERY_WINDOWS_MANUAL_INSTALL_REPAIR_OK'
