# Disposable standard-user probe: status and fixed pause toggle; no maintenance launch.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub runner required.' }
$userName = 'SdeRead' + [guid]::NewGuid().ToString('N').Substring(0,8)
$fixture = Join-Path 'C:\Users\Public' $userName
New-Item -ItemType Directory -Path $fixture | Out-Null
$probe = Join-Path $fixture 'probe.ps1'
@'
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Expected a standard student account.' }
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
$result = & $worker self-update-status | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $null -eq $result.paused -or $null -eq $result.checkedAt -or $result.toolExit -ne 0) { throw 'Student could not read complete policy/status.' }
foreach ($verb in @('pause','resume')) {
    $deniedProcess = Start-Process -FilePath $worker -ArgumentList $verb -Wait -PassThru -WindowStyle Hidden
    if ($deniedProcess.ExitCode -eq 0) { throw 'Student changed pause policy.' }
}
$originalPaused = $result.paused
foreach ($verb in @('set-paused','set-enabled')) {
    & $worker $verb
    if ($LASTEXITCODE -ne 0) { throw 'Student could not change the fixed pause preference.' }
    $current = & $worker self-update-status | ConvertFrom-Json
    if ($current.paused -ne ($verb -eq 'set-paused') -or $current.checkedAt -ne $result.checkedAt -or $current.toolExit -ne $result.toolExit) { throw 'Setting change altered history or was not observed.' }
}
$restore = if ($originalPaused) { 'set-paused' } else { 'set-enabled' }
& $worker $restore
if ($LASTEXITCODE -ne 0) { throw 'Student setting restore failed.' }
$parent = 'C:\ProgramData\SkyviewRobotics'
foreach ($directory in @($parent,(Join-Path $parent 'Logs'))) {
    $denied = $false
    $probePath = Join-Path $directory ('student-write-probe-' + [guid]::NewGuid().ToString('N'))
    try { [IO.File]::WriteAllText($probePath,'unsafe') }
    catch [UnauthorizedAccessException] { $denied = $true }
    if (-not $denied) { throw 'Student could create maintenance-parent or Logs files.' }
}
$legacyLog = Join-Path $parent 'Logs\AutoUpdate-20261014-051807.log'
$denied = $false
try {
    $handle = [IO.File]::Open($legacyLog,[IO.FileMode]::Open,[IO.FileAccess]::Write)
    $handle.Dispose()
} catch [UnauthorizedAccessException] { $denied = $true }
if (-not $denied) { throw 'Student could open migrated legacy evidence for writing.' }
$denied = $false
try {
    $handle = [IO.File]::Open((Join-Path $parent 'Update-SkyviewTools.ps1'),[IO.FileMode]::Open,[IO.FileAccess]::Write)
    $handle.Dispose()
} catch [UnauthorizedAccessException] { $denied = $true }
if (-not $denied) { throw 'Student could open the applied baseline for writing.' }
foreach ($name in @('status.json')) {
    $path = Join-Path 'C:\ProgramData\SkyviewRobotics\SelfUpdate' $name
    $denied = $false
    try { [IO.File]::WriteAllText($path,'unsafe') } catch [UnauthorizedAccessException] { $denied = $true }
    if (-not $denied) { throw 'Student could overwrite public receipts.' }
}
foreach ($name in @('active.json','installation.json','recovery.json')) {
    $path = Join-Path 'C:\ProgramData\SkyviewRobotics\SelfUpdate' $name
    $denied = $false
    try { [void][IO.File]::ReadAllText($path) }
    catch [UnauthorizedAccessException] { $denied = $true }
    catch [IO.FileNotFoundException] {
        # Native failure coverage deliberately removes test-key recovery state.
        # Missing recovery must still be protected against student creation.
        if ($name -ne 'recovery.json') { throw }
        try { [IO.File]::WriteAllText($path,'{}') }
        catch [UnauthorizedAccessException] { $denied = $true }
    }
    if (-not $denied) { throw "Student could read or create private installation state: $name." }
}
Write-Output 'SDE_STANDARD_USER_STATUS_OK'
exit 0
'@ | Set-Content -LiteralPath $probe -Encoding UTF8
$password = ConvertTo-SecureString ('Ci!' + [guid]::NewGuid().ToString('N') + 'aA7') -AsPlainText -Force
$credential = New-Object Management.Automation.PSCredential("$env:COMPUTERNAME\$userName",$password)
$root = 'C:\ProgramData\SkyviewRobotics\SelfUpdate'
$before = (Get-Content (Join-Path $root 'policy.json') -Raw | ConvertFrom-Json).paused
try {
    New-LocalUser -Name $userName -Password $password -AccountNeverExpires -PasswordNeverExpires | Out-Null
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $userName
    Start-Service -Name seclogon
    $stdout = Join-Path $fixture 'stdout.txt'
    $stderr = Join-Path $fixture 'stderr.txt'
    $process = Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$probe`"" -Credential $credential -LoadUserProfile -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    [void]$process.Handle
    if (-not $process.WaitForExit(45000)) { throw 'Read-only probe timed out; no package process was launched.' }
    $output = Get-Content -LiteralPath $stdout -Raw
    if (($null -ne $process.ExitCode -and $process.ExitCode -ne 0) -or $output -notmatch '(?m)^SDE_STANDARD_USER_STATUS_OK\s*$') {
        throw "Standard-user probe failed: $output $(Get-Content -LiteralPath $stderr -Raw)"
    }
    if ($before -ne (Get-Content (Join-Path $root 'policy.json') -Raw | ConvertFrom-Json).paused) { throw 'Student did not restore the pause preference.' }
    Write-Host $output
} finally { Remove-LocalUser -Name $userName -ErrorAction SilentlyContinue }
