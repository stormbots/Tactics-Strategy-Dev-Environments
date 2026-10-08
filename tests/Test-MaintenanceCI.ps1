param([switch]$CheckInstalledTask)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Task permission tests are restricted to disposable GitHub runners.' }
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/ScheduledMaintenance.ps1')
$suffix = [guid]::NewGuid().ToString('N').Substring(0,8)
$userName = "SkyTask$suffix"
$taskName = "Skyview CI maintenance $suffix"
$fixture = Join-Path 'C:\Users\Public' "Skyview maintenance probe $suffix"
New-Item -ItemType Directory -Path $fixture | Out-Null
Copy-Item (Join-Path $PSScriptRoot '../windows/chocolatey/tools/ScheduledMaintenance.ps1') $fixture
Copy-Item (Join-Path $PSScriptRoot '../windows/chocolatey/tools/Inspect-SkyviewSchedule.ps1') $fixture
$probe = Join-Path $fixture 'Probe.ps1'
@'
param($TaskName,$ExpectedStatus,$ExpectedMessage,[switch]$DenyControl)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ScheduledMaintenance.ps1')
. (Join-Path $PSScriptRoot 'Inspect-SkyviewSchedule.ps1')
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Probe must run as a standard user.' }
$result = Get-SkyviewMaintenanceResult -TaskName $TaskName
Write-Output ($result | ConvertTo-Json -Compress)
if ($result.Status -ne $ExpectedStatus -or $result.Message -notlike "*$ExpectedMessage*") { throw 'Unexpected maintenance validation result.' }
if ($DenyControl) {
    $service = New-Object -ComObject Schedule.Service
    $service.Connect()
    $task = $service.GetFolder('\').GetTask($TaskName)
    $schedule = ConvertTo-SkyviewSchedule -Task $task
    if ($schedule.status -ne 'enabled' -or $schedule.lastResult -ne 'never') { throw 'Normal user could not read schedule details.' }
    foreach ($operation in @('run','change permissions')) {
        $denied = $false
        try {
            if ($operation -eq 'run') { [void]$task.Run($null) }
            else { $task.SetSecurityDescriptor('D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FR;;;BU)',0) }
        }
        catch {
            $e = $_.Exception
            while ($e.InnerException) { $e = $e.InnerException }
            if ($e.HResult.ToString('X8') -ne '80070005') { throw }
            $denied = $true
        }
        if (-not $denied) { throw "Standard user could $operation the SYSTEM task." }
    }
}
Write-Output 'STANDARD_USER_TASK_CHECK_OK'
exit 0
'@ | Set-Content -LiteralPath $probe -Encoding UTF8
$password = ConvertTo-SecureString ("Ci!" + [guid]::NewGuid().ToString('N') + 'aA7') -AsPlainText -Force
$credential = New-Object Management.Automation.PSCredential("$env:COMPUTERNAME\$userName",$password)
function Invoke-StandardUserProbe($Name,$Status,$Message,[switch]$DenyControl) {
    $stdout = Join-Path $fixture 'stdout.txt'
    $stderr = Join-Path $fixture 'stderr.txt'
    $arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$probe`" -TaskName `"$Name`" -ExpectedStatus $Status -ExpectedMessage `"$Message`""
    if ($DenyControl) { $arguments += ' -DenyControl' }
    $process = Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList $arguments -Credential $credential -LoadUserProfile -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    [void]$process.Handle
    if (-not $process.WaitForExit(45000)) { $process.Kill(); throw 'Standard-user task probe timed out.' }
    $exitCode = $process.ExitCode
    $output = Get-Content -LiteralPath $stdout -Raw
    # Windows PowerShell 5.1 can leave ExitCode null for credentialed children.
    # The marker is emitted only after every assertion; all reported nonzero
    # exit codes and missing markers still fail the test.
    if (($null -ne $exitCode -and $exitCode -ne 0) -or $output -notmatch '(?m)^STANDARD_USER_TASK_CHECK_OK\s*$') {
        throw "Standard-user task probe failed (exit $exitCode): $output $(Get-Content -LiteralPath $stderr -Raw)"
    }
    Write-Host $output
}
try {
    New-LocalUser -Name $userName -Password $password -AccountNeverExpires -PasswordNeverExpires | Out-Null
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $userName
    Start-Service -Name seclogon
    # A harmless SYSTEM fixture lets us assert that users cannot execute or
    # modify a task without ever trying to start real maintenance.
    $action = New-ScheduledTaskAction -Execute 'C:\Windows\System32\cmd.exe' -Argument '/d /c exit 0'
    Register-ScheduledTask -TaskName $taskName -Action $action -User SYSTEM -RunLevel Highest -Force | Out-Null
    $scheduler = New-Object -ComObject Schedule.Service
    $scheduler.Connect()
    $registered = $scheduler.GetFolder('\').GetTask($taskName)
    $registered.SetSecurityDescriptor('D:P(A;;FA;;;SY)(A;;FA;;;BA)',0)
    Invoke-StandardUserProbe $taskName FAIL 'cannot be read'
    Set-SkyviewMaintenanceReadAccess -TaskName $taskName
    Invoke-StandardUserProbe $taskName PASS 'Weekly maintenance enabled' -DenyControl
    $registered.Enabled = $false
    Invoke-StandardUserProbe $taskName FAIL 'disabled'
    Invoke-StandardUserProbe "$taskName missing" FAIL 'missing'
    if ($CheckInstalledTask) {
        Invoke-StandardUserProbe 'Skyview Robotics - Dev Tool Updates' PASS 'Weekly maintenance enabled'
    }
    Write-Host 'SKYVIEW_MAINTENANCE_PERMISSIONS_OK'
}
finally {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Remove-LocalUser -Name $userName -ErrorAction SilentlyContinue
}
