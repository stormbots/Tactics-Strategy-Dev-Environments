# Disposable standard-user probe: fixed read command, no maintenance launch.
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
foreach ($name in @('policy.json','status.json')) {
    $path = Join-Path 'C:\ProgramData\SkyviewRobotics\SelfUpdate' $name
    $denied = $false
    try { [IO.File]::WriteAllText($path,'unsafe') } catch [UnauthorizedAccessException] { $denied = $true }
    if (-not $denied) { throw 'Student could overwrite public receipts.' }
}
foreach ($name in @('active.json','installation.json','recovery.json')) {
    $path = Join-Path 'C:\ProgramData\SkyviewRobotics\SelfUpdate' $name
    $denied = $false
    try { [void][IO.File]::ReadAllText($path) } catch [UnauthorizedAccessException] { $denied = $true }
    if (-not $denied) { throw 'Student could read private installation state.' }
}
Write-Output 'SDE_STANDARD_USER_STATUS_OK'
exit 0
'@ | Set-Content -LiteralPath $probe -Encoding UTF8
$password = ConvertTo-SecureString ('Ci!' + [guid]::NewGuid().ToString('N') + 'aA7') -AsPlainText -Force
$credential = New-Object Management.Automation.PSCredential("$env:COMPUTERNAME\$userName",$password)
$root = 'C:\ProgramData\SkyviewRobotics\SelfUpdate'
$before = [IO.File]::ReadAllBytes((Join-Path $root 'policy.json'))
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
    if ([Convert]::ToBase64String($before) -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $root 'policy.json')))) { throw 'Student altered policy.' }
    Write-Host $output
} finally { Remove-LocalUser -Name $userName -ErrorAction SilentlyContinue }
