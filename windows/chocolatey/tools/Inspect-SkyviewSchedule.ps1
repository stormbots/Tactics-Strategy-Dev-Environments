[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding

function ConvertTo-SkyviewSchedule {
    param($Task)
    [xml]$definition = $Task.Xml
    $frequency = @()
    $hasEnabledTrigger = $false
    foreach ($trigger in $definition.Task.Triggers.ChildNodes) {
        if ($trigger.Enabled -eq 'false') { continue }
        $hasEnabledTrigger = $true
        if ($trigger.ScheduleByWeek) {
            $days = @($trigger.ScheduleByWeek.DaysOfWeek.ChildNodes | ForEach-Object { $_.LocalName }) -join ', '
            $boundary = [datetime]$trigger.StartBoundary
            if ($boundary.Kind -eq [DateTimeKind]::Utc) { $boundary = $boundary.ToLocalTime() }
            $time = $boundary.ToString('HH:mm')
            $frequency += "Every $($trigger.ScheduleByWeek.WeeksInterval) week(s), $days at $time"
        } else {
            $frequency += "$($trigger.LocalName): $($trigger.StartBoundary)"
        }
    }
    $last = $null; $next = $null
    if ([datetime]$Task.LastRunTime -gt [datetime]'2000-01-01') { $last = ([datetimeoffset]([datetime]$Task.LastRunTime)).ToString('o') }
    # Scheduler may report a next time for disabled triggers. Hide it unless
    # both the task and at least one of its triggers are enabled.
    if ($Task.Enabled -and $hasEnabledTrigger -and [datetime]$Task.NextRunTime -gt [datetime]'2000-01-01') { $next = ([datetimeoffset]([datetime]$Task.NextRunTime)).ToString('o') }
    $result = if ($Task.State -in @(2,4)) { 'running' } elseif (-not $last) { 'never' } elseif ($Task.LastTaskResult -eq 0) { 'success' } else { 'failure' }
    $code = [int64]$Task.LastTaskResult -band 0xffffffffL
    [pscustomobject]@{
        status = $(if ($Task.Enabled) { 'enabled' } else { 'disabled' })
        active = [bool]($Task.State -in @(2,3,4))
        identifier = '\Skyview Robotics - Dev Tool Updates'
        frequency = $(if ($frequency.Count) { ($frequency -join '; ') + ' (local time)' } else { 'No enabled time trigger' })
        nextRun = $next; lastRun = $last; lastResult = $result
        resultDetail = $(if ($last) { 'Task Scheduler result: 0x{0:X8}' -f $code } else { 'This task has never run.' })
        catchUp = [bool]($definition.Task.Settings.StartWhenAvailable -eq 'true')
        logFolder = 'C:\ProgramData\SkyviewRobotics\Logs'
        logsAvailable = [bool](Test-Path -LiteralPath 'C:\ProgramData\SkyviewRobotics\Logs' -PathType Container)
        note = ''
    }
}
function Get-SkyviewSchedule {
    try {
        $scheduler = New-Object -ComObject 'Schedule.Service'
        $scheduler.Connect()
        $task = $scheduler.GetFolder('\').GetTask('Skyview Robotics - Dev Tool Updates')
        ConvertTo-SkyviewSchedule -Task $task
    } catch {
        $exception = $_.Exception
        while ($exception.InnerException) { $exception = $exception.InnerException }
        $code = '{0:X8}' -f ($exception.HResult -band 0xffffffffL)
        $missing = $code -in @('80070002', '80070003')
        [pscustomobject]@{
            status = $(if ($missing) { 'missing' } else { 'unavailable' }); active=$false
            identifier='\Skyview Robotics - Dev Tool Updates'; frequency='Unavailable'
            nextRun=$null; lastRun=$null; lastResult='unavailable'; resultDetail='Unavailable'
            catchUp=$null; logFolder='C:\ProgramData\SkyviewRobotics\Logs'
            logsAvailable=[bool](Test-Path -LiteralPath 'C:\ProgramData\SkyviewRobotics\Logs' -PathType Container)
            note=$(if ($missing) { 'Weekly maintenance is not installed. Use Install or Repair on Overview.' } elseif ($code -eq '80070005') { 'This account cannot read the task. Use Repair on Overview to restore read access.' } else { "Task Scheduler information could not be read (0x$code)." })
        }
    }
}
if ($MyInvocation.InvocationName -ne '.') { Get-SkyviewSchedule | ConvertTo-Json -Compress }
