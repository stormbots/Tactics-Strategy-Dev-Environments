param([Parameter(Mandatory=$true)][string]$FixtureRoot,
      [Parameter(Mandatory=$true)][string]$TestBinary)
# Called only by the Rust test binary with an isolated, synthetic fixture.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub runner required.' }
if ($FixtureRoot -notmatch '^C:\\ProgramData\\coordination-test-[0-9]+-[0-9]+$') { throw 'Unexpected fixture root.' }
# Pin the in-box 5.1 security module, not a same-named PowerShell 7 module
# inherited through a pwsh -> Rust -> Windows PowerShell process chain.
Import-Module "$PSHOME\Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1" -ErrorAction Stop
$userName = 'SdeStore' + [guid]::NewGuid().ToString('N').Substring(0,8)
$work = Join-Path 'C:\Users\Public' ('SdeStoreProbe-' + [guid]::NewGuid().ToString('N'))
$createdUser = $false
$process = $null
try {
    New-Item -ItemType Directory -Path $work | Out-Null
    # Copy the test executable only, never a privileged worker or package. The
    # checkout's enclosing ACLs must not decide whether the student probe runs.
    $binary = Join-Path $work 'storage-probe.exe'
    Copy-Item -LiteralPath $TestBinary -Destination $binary
    $bridge = Join-Path $work 'student-probe.ps1'
    @'
param([string]$FixtureRoot)
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Expected a standard student account.' }
# Pass the fixture identity inside the standard account's own process rather
# than assuming CreateProcessWithLogonW inherits the caller's environment.
$env:SDE_TEST_RECOVERY_DIR = $FixtureRoot
& (Join-Path $PSScriptRoot 'storage-probe.exe') --exact tests::recovery_student_probe --nocapture
exit $LASTEXITCODE
'@ | Set-Content -LiteralPath $bridge -Encoding UTF8
    $password = ConvertTo-SecureString ('Ci!' + [guid]::NewGuid().ToString('N') + 'aA7') -AsPlainText -Force
    $credential = New-Object Management.Automation.PSCredential("$env:COMPUTERNAME\$userName",$password)
    New-LocalUser -Name $userName -Password $password -AccountNeverExpires -PasswordNeverExpires | Out-Null
    $createdUser = $true
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $userName
    Start-Service -Name seclogon
    $stdout = Join-Path $work 'stdout.txt'
    $stderr = Join-Path $work 'stderr.txt'
    $process = Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$bridge`" -FixtureRoot `"$FixtureRoot`"" -Credential $credential -LoadUserProfile -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    [void]$process.Handle
    if (-not $process.WaitForExit(45000)) { throw 'Synthetic storage probe timed out; no package was launched.' }
    $output = Get-Content -LiteralPath $stdout -Raw
    if (($null -ne $process.ExitCode -and $process.ExitCode -ne 0) -or $output -notmatch '(?m)^SDE_RECOVERY_PRODUCTION_STUDENT_SUBMISSION_OK\s*$') {
        throw "Production storage student probe failed: $output $(Get-Content -LiteralPath $stderr -Raw)"
    }
    Write-Output 'SDE_RECOVERY_PRODUCTION_STUDENT_SUBMISSION_OK'
} finally {
    if ($process) {
        if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
        $process.Dispose()
    }
    if ($createdUser) { Remove-LocalUser -Name $userName -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $work) { Remove-Item -LiteralPath $work -Recurse -Force }
}
