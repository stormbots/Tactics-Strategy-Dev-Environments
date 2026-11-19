[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding

function Get-SkyviewChoiceContext {
    param($Task)
    # Display preference binding only: no mutation, elevation or permission changes.
    try {
        $xml = [string]$Task.Xml
        if (-not $xml -or $xml.Length -gt 65536) { return }
        [xml]$definition = $xml
        $actions = @($definition.Task.Actions.ChildNodes)
        if ($actions.Count -ne 1 -or $actions[0].LocalName -ne 'Exec') { return }
        if ($actions[0].Command -ine 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe') { return }
        $approved = @(
            '-NoProfile -ExecutionPolicy Bypass -File "C:\ProgramData\SkyviewRobotics\AutoUpdate-SkyviewTools.ps1"',
            '-NoProfile -ExecutionPolicy Bypass -File "C:\ProgramData\SkyviewRobotics\SelfUpdate\Invoke-SkyviewMaintenance.ps1"'
        )
        if ([string]$actions[0].Arguments -notin $approved) { return }
        if ([string]$definition.Task.Principals.Principal.UserId -notin @('S-1-5-18', 'SYSTEM')) { return }
        $security = New-Object Security.AccessControl.RawSecurityDescriptor($Task.GetSecurityDescriptor(1))
        if ($security.Owner.Value -notin @('S-1-5-18', 'S-1-5-32-544')) { return }
        $registry = [Microsoft.Win32.RegistryKey]::OpenBaseKey('LocalMachine', 'Registry64')
        try {
            $key = $registry.OpenSubKey('SOFTWARE\Microsoft\Cryptography', $false)
            try { $machine = [string]$key.GetValue('MachineGuid', $null) } finally { if ($key) { $key.Dispose() } }
        } finally { $registry.Dispose() }
        $guid = [guid]::Empty
        if ($machine.Length -gt 40 -or -not [guid]::TryParse($machine, [ref]$guid) -or $guid -eq [guid]::Empty) { return }
        $hash = [Security.Cryptography.SHA256]::Create()
        try {
            $machineHash = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes("sde-maintenance-machine-v1`0" + $guid.ToString('D')))).Replace('-', '').ToLowerInvariant()
            $definitionHash = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($xml))).Replace('-', '').ToLowerInvariant()
        } finally { $hash.Dispose() }
        @{ machineId=$machineHash; identifier='\Skyview Robotics - Dev Tool Updates'; definitionId=$definitionHash }
    } catch { return } # A context failure must not hide a readable schedule.
}

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
    $result = if ($Task.State -in @(2,4)) { 'running' } elseif (-not $last) { 'never' } elseif ($Task.LastTaskResult -eq 75) { 'deferred' } elseif ($Task.LastTaskResult -eq 0) { 'success' } else { 'failure' }
    $code = [int64]$Task.LastTaskResult -band 0xffffffffL
    $observed = [datetimeoffset]::UtcNow.ToString('o')
    $record = [pscustomobject]@{
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
        inspectionScope = 'schedule'
        inspectionReason = 'verified'
        observedAt = $observed
        createdAt = $null
        lastSuccess = $(if ($result -eq 'success') { $last } else { $null })
    }
    $context = Get-SkyviewChoiceContext -Task $Task
    if ($context) { $record | Add-Member -NotePropertyName choiceContext -NotePropertyValue $context }
    $record
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
            inspectionScope='schedule'
            inspectionReason=$(if ($missing) { 'notInstalled' } elseif ($code -eq '80070005') { 'accessDenied' } else { 'readFailed' })
            status = $(if ($missing) { 'missing' } else { 'unavailable' }); active=$false
            identifier='\Skyview Robotics - Dev Tool Updates'; frequency='Unavailable'
            nextRun=$null; lastRun=$null; lastResult='unavailable'; resultDetail='Unavailable'
            catchUp=$null; logFolder='C:\ProgramData\SkyviewRobotics\Logs'
            logsAvailable=[bool](Test-Path -LiteralPath 'C:\ProgramData\SkyviewRobotics\Logs' -PathType Container)
            note=$(if ($missing) { 'Weekly maintenance is not installed. Review the schedule before choosing any setup changes.' } elseif ($code -eq '80070005') { 'SDE does not have permission to read this task. Check access with your teacher or administrator, then refresh. Your task has not been changed.' } else { "SDE could not read the task information (0x$code). Refresh and save a support report if the check still fails." })
            observedAt=[datetimeoffset]::UtcNow.ToString('o'); createdAt=$null; lastSuccess=$null
        }
    }
}
if ($MyInvocation.InvocationName -ne '.') { Get-SkyviewSchedule | ConvertTo-Json -Compress }
