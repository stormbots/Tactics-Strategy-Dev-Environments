# Run using the companion CMD file. Requires an existing SDE maintenance setup.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    try {
        $arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '"'
        $child = Start-Process -FilePath "$PSHOME\powershell.exe" -Verb RunAs -ArgumentList $arguments -Wait -PassThru
        exit $child.ExitCode
    } catch {
        Write-Host "Administrator approval failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}
$code = 1
$transcribing = $false
try {
    if (-not [Environment]::Is64BitProcess) { throw 'Use the companion CMD file to launch 64-bit PowerShell.' }
    $worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
    $taskName = 'Skyview Robotics - Dev Tool Updates'
    if (-not (Test-Path -LiteralPath $worker -PathType Leaf)) { throw 'Installed SDE updater is missing. Install the authenticated stable SDE package first.' }
    $task = Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction Stop
    if ($task.Principal.UserId -notin @('SYSTEM', 'S-1-5-18', 'NT AUTHORITY\SYSTEM')) { throw 'Maintenance task is not configured for SYSTEM. Mentor review is required.' }
    if (@($task.Triggers).Count -eq 0) { throw 'Maintenance task has no existing schedule. Mentor review is required.' }
    $launcher = 'C:\ProgramData\SkyviewRobotics\SelfUpdate\Invoke-SkyviewMaintenance.ps1'
    if (@($task.Actions | Where-Object { $_.Arguments -and $_.Arguments.IndexOf($launcher, [StringComparison]::OrdinalIgnoreCase) -ge 0 }).Count -ne 1) {
        throw 'Maintenance task does not use the installed SDE self-update launcher. Mentor review is required.'
    }
    $log = Join-Path $env:SystemRoot ('Temp\SDE-Maintenance-' + [guid]::NewGuid().ToString() + '.log')
    Start-Transcript -Path $log -NoClobber | Out-Null
    $transcribing = $true
    Write-Host "Computer: $env:COMPUTERNAME"
    Write-Host 'Close SDE normally. Keep the laptop powered and online.' -ForegroundColor Yellow
    Write-Host 'Enabling automatic SDE app updates (future stable releases included)...'
    & $worker resume
    if ($LASTEXITCODE -ne 0) { throw 'Updater resume failed. Schedule was not changed and maintenance was not requested.' }
    $policy = (& $worker self-update-status) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw 'Could not read updater status after resume.' }
    $status = $policy | ConvertFrom-Json
    if ($status.paused -ne $false) { throw 'Updater did not confirm paused=false.' }
    Enable-ScheduledTask -TaskName $taskName -TaskPath '\' | Out-Null
    $task = Get-ScheduledTask -TaskName $taskName -TaskPath '\'
    if ($task.State -eq 'Disabled') { throw 'Maintenance task is still disabled.' }
    if ($task.State -eq 'Running') {
        Write-Host 'Maintenance is already running; no second run was requested.'
    } else {
        Start-ScheduledTask -TaskName $taskName -TaskPath '\'
        Write-Host 'Maintenance start requested.' -ForegroundColor Green
    }
    Write-Host 'Automatic app updates and the existing maintenance schedule are enabled.'
    Write-Host 'This is a launch confirmation, not proof the update finished.'
    Write-Host 'When maintenance finishes, reopen SDE: check About and Schedule.'
    Write-Host 'Today the target is 1.2.9; future runs select the highest eligible stable release.'
    Write-Host "Local launcher log: $log"
    Write-Host 'You may remove the flash drive after closing this launcher.'
    $code = 0
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Earlier successful changes may remain enabled. Do not assume maintenance started.' -ForegroundColor Yellow
} finally {
    if ($transcribing) { Stop-Transcript | Out-Null }
    [void](Read-Host 'Press Enter to close')
}
exit $code
