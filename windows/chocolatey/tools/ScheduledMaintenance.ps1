# Only the Skyview-managed task is given read access for normal users.
# Task Scheduler uses file rights: FR excludes execute, write, delete and WriteDAC.
# https://learn.microsoft.com/en-us/windows/win32/taskschd/security-contexts-for-running-tasks
function Set-SkyviewMaintenanceReadAccess {
    param([string]$TaskName = 'Skyview Robotics - Dev Tool Updates')
    $scheduler = New-Object -ComObject Schedule.Service
    $scheduler.Connect()
    $task = $scheduler.GetFolder('\').GetTask($TaskName)
    $task.SetSecurityDescriptor('D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FR;;;BU)', 0)
}

function Get-SkyviewMaintenanceResult {
    param([string]$TaskName = 'Skyview Robotics - Dev Tool Updates')
    try {
        # Query the exact task directly, avoiding a CIM enumeration that can
        # silently omit administrator-created tasks in a standard user session.
        $scheduler = New-Object -ComObject Schedule.Service
        $scheduler.Connect()
        $task = $scheduler.GetFolder('\').GetTask($TaskName)
        if ($task.Enabled) {
            return @{Status='INFO'; ScheduleStatus='enabled'; Message='Weekly maintenance is enabled. View Schedule for its next run and earlier results.'}
        }
        return @{Status='INFO'; ScheduleStatus='disabled'; Message='Weekly maintenance is disabled. This task will not start future automatic development-tool maintenance. Review Schedule.'}
    }
    catch {
        $exception = $_.Exception
        while ($exception.InnerException) { $exception = $exception.InnerException }
        $code = $exception.HResult.ToString('X8')
        $message = switch ($code) {
            '80070005' { 'Weekly maintenance could not be checked because this account cannot read the task. Review Schedule and save a support report if access is still denied.' }
            { $_ -in @('80070002','80070003') } { 'Weekly maintenance task is missing. Review Schedule before choosing any setup changes.' }
            default { "Weekly maintenance could not be checked ($code). Review Schedule and save a support report if the check still fails." }
        }
        $state = if ($code -in @('80070002','80070003')) { 'missing' } else { 'unavailable' }
        return @{Status='INFO'; ScheduleStatus=$state; Message=$message}
    }
}
