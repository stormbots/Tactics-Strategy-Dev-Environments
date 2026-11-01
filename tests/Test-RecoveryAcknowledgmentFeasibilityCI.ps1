# T1 permission-layout experiment only. No production paths, workers, or packages.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub runner required.' }
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Privileged fixture setup required.' }
$suffix = [guid]::NewGuid().ToString('N')
$userName = 'SdeAck' + $suffix.Substring(0,8)
$fixture = Join-Path 'C:\ProgramData' ('SdeRecoveryContract-' + $suffix)
$outputDirectory = Join-Path 'C:\Users\Public' ('SdeRecoveryProbe-' + $suffix)
$privateSddl = 'O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)'
$publicSddl = $privateSddl + '(A;;FR;;;BU)'
$slotSddl = $privateSddl + '(A;;0x12019f;;;BU)'
$process = $null
$createdUser = $false
function Set-FixtureFileAcl([string]$Path,[string]$Sddl) {
    $security = New-Object Security.AccessControl.FileSecurity
    $security.SetSecurityDescriptorSddlForm($Sddl)
    Set-Acl -LiteralPath $Path -AclObject $security
}
try {
    New-Item -ItemType Directory -Path $fixture | Out-Null
    $directoryAcl = New-Object Security.AccessControl.DirectorySecurity
    $directoryAcl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FRFX;;;BU)')
    Set-Acl -LiteralPath $fixture -AclObject $directoryAcl
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
    $journal = Join-Path $fixture 'transaction.json'
    # Explicitly synthetic bytes: never read or copy the owner's transaction.
    [IO.File]::WriteAllText($journal,'{"schema":1,"token":"private-fixture-token","kind":"system"}')
    Set-FixtureFileAcl $journal $privateSddl
    $journalHash = (Get-FileHash -LiteralPath $journal -Algorithm SHA256).Hash
    $journalAcl = (Get-Acl -LiteralPath $journal).Sddl
    $incidentId = [guid]::NewGuid().ToString()
    $snapshot = Join-Path $fixture 'recovery-incident.json'
    [IO.File]::WriteAllText($snapshot,(@{schema=1;incidentId=$incidentId} | ConvertTo-Json -Compress))
    Set-FixtureFileAcl $snapshot $publicSddl
    $snapshotHash = (Get-FileHash -LiteralPath $snapshot -Algorithm SHA256).Hash
    $binding = Join-Path $fixture 'recovery-binding.json'
    [IO.File]::WriteAllText($binding,(@{incidentId=$incidentId;journalSha256=$journalHash} | ConvertTo-Json -Compress))
    Set-FixtureFileAcl $binding $privateSddl
    $bindingHash = (Get-FileHash -LiteralPath $binding -Algorithm SHA256).Hash
    $slot = Join-Path $fixture 'recovery-acknowledgment.json'
    [IO.File]::WriteAllText($slot,'{}')
    Set-FixtureFileAcl $slot $slotSddl
    $slotAcl = (Get-Acl -LiteralPath $slot).Sddl
    $probe = Join-Path $fixture 'student-probe.ps1'
    @'
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Expected a standard student account.' }
$root = $PSScriptRoot
$snapshot = Get-Content -LiteralPath (Join-Path $root 'recovery-incident.json') -Raw | ConvertFrom-Json
if ($snapshot.schema -ne 1 -or @($snapshot.PSObject.Properties).Count -ne 2) { throw 'Invalid public snapshot.' }
$slot = Join-Path $root 'recovery-acknowledgment.json'
[IO.File]::WriteAllText($slot,(@{schema=1;incidentId=$snapshot.incidentId} | ConvertTo-Json -Compress))
foreach ($attempt in @('read journal','read binding','write journal','delete journal','write snapshot','create sibling','delete slot','change slot ACL')) {
    $denied = $false
    try {
        switch ($attempt) {
            'read journal' { [void][IO.File]::ReadAllText((Join-Path $root 'transaction.json')) }
            'read binding' { [void][IO.File]::ReadAllText((Join-Path $root 'recovery-binding.json')) }
            'write journal' { [IO.File]::WriteAllText((Join-Path $root 'transaction.json'),'unsafe') }
            'delete journal' { [IO.File]::Delete((Join-Path $root 'transaction.json')) }
            'write snapshot' { [IO.File]::WriteAllText((Join-Path $root 'recovery-incident.json'),'unsafe') }
            'create sibling' { [IO.File]::WriteAllText((Join-Path $root 'new-state'),'unsafe') }
            'delete slot' { [IO.File]::Delete($slot) }
            'change slot ACL' {
                $acl = New-Object Security.AccessControl.FileSecurity
                $acl.SetSecurityDescriptorSddlForm('D:P(A;;FA;;;BU)')
                [IO.File]::SetAccessControl($slot,$acl)
            }
        }
    } catch {
        $errorDetail = $_.Exception
        while ($errorDetail.InnerException) { $errorDetail = $errorDetail.InnerException }
        if ($errorDetail -isnot [UnauthorizedAccessException]) { throw }
        $denied = $true
    }
    if (-not $denied) { throw "Student could $attempt." }
}
Write-Output 'SDE_RECOVERY_WINDOWS_STANDARD_USER_INTENT_OK'
exit 0
'@ | Set-Content -LiteralPath $probe -Encoding UTF8
    # Follow the repository's existing disposable standard-account probe pattern.
    $password = ConvertTo-SecureString ('Ci!' + [guid]::NewGuid().ToString('N') + 'aA7') -AsPlainText -Force
    $credential = New-Object Management.Automation.PSCredential("$env:COMPUTERNAME\$userName",$password)
    New-LocalUser -Name $userName -Password $password -AccountNeverExpires -PasswordNeverExpires | Out-Null
    $createdUser = $true
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $userName
    Start-Service -Name seclogon
    $stdout = Join-Path $outputDirectory 'stdout.txt'
    $stderr = Join-Path $outputDirectory 'stderr.txt'
    $process = Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$probe`"" -Credential $credential -LoadUserProfile -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    [void]$process.Handle
    if (-not $process.WaitForExit(45000)) { throw 'Synthetic acknowledgment probe timed out; no packages were launched.' }
    $output = Get-Content -LiteralPath $stdout -Raw
    if (($null -ne $process.ExitCode -and $process.ExitCode -ne 0) -or $output -notmatch '(?m)^SDE_RECOVERY_WINDOWS_STANDARD_USER_INTENT_OK\s*$') {
        throw "Standard-user acknowledgment probe failed: $output $(Get-Content -LiteralPath $stderr -Raw)"
    }
    if ((Get-FileHash -LiteralPath $journal -Algorithm SHA256).Hash -cne $journalHash -or (Get-Acl -LiteralPath $journal).Sddl -cne $journalAcl) { throw 'Original fixture evidence or permissions changed.' }
    if ((Get-FileHash -LiteralPath $binding -Algorithm SHA256).Hash -cne $bindingHash) { throw 'Private binding changed.' }
    if ((Get-FileHash -LiteralPath $snapshot -Algorithm SHA256).Hash -cne $snapshotHash) { throw 'Public incident changed.' }
    if ((Get-Acl -LiteralPath $slot).Sddl -cne $slotAcl) { throw 'Intent slot permissions changed.' }
    # A new independent privileged consumer represents a later scheduled process.
    $consumer = @'
param($Root,$Expected)
$ErrorActionPreference = 'Stop'
$intent = Get-Content -LiteralPath (Join-Path $Root 'recovery-acknowledgment.json') -Raw | ConvertFrom-Json
$binding = Get-Content -LiteralPath (Join-Path $Root 'recovery-binding.json') -Raw | ConvertFrom-Json
$hash = (Get-FileHash -LiteralPath (Join-Path $Root 'transaction.json') -Algorithm SHA256).Hash
if ($intent.schema -ne 1 -or @($intent.PSObject.Properties).Count -ne 2 -or $intent.incidentId -cne $Expected -or $intent.incidentId -cne $binding.incidentId -or $hash -cne $binding.journalSha256) { throw 'Cross-process private binding did not match.' }
Write-Output 'SDE_RECOVERY_WINDOWS_PRIVILEGED_CONSUMER_OK'
exit 0
'@
    $consumerPath = Join-Path $fixture 'consumer-probe.ps1'
    Set-Content -LiteralPath $consumerPath -Value $consumer -Encoding UTF8
    $consumerOutput = & 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $consumerPath $fixture $incidentId
    if ($LASTEXITCODE -ne 0 -or $consumerOutput -notcontains 'SDE_RECOVERY_WINDOWS_PRIVILEGED_CONSUMER_OK') { throw 'Independent consumer failed.' }
    Write-Host 'SDE_RECOVERY_WINDOWS_STANDARD_USER_INTENT_OK'
    Write-Host 'SDE_RECOVERY_WINDOWS_PRIVILEGED_CONSUMER_OK'
} finally {
    # Only the disposable child/account and the two explicit GUID fixture paths.
    # This synthetic process never starts a package installer or maintenance.
    if ($process) {
        if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
        $process.Dispose()
    }
    if ($createdUser) { Remove-LocalUser -Name $userName -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $fixture) { Remove-Item -LiteralPath $fixture -Recurse -Force }
    if (Test-Path -LiteralPath $outputDirectory) { Remove-Item -LiteralPath $outputDirectory -Recurse -Force }
}
