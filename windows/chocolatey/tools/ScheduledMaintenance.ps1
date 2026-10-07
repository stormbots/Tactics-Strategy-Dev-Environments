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
            return @{Status='PASS'; Message='Weekly maintenance enabled'}
        }
        return @{Status='FAIL'; Message='Weekly maintenance is disabled. Run Repair to enable it.'}
    }
    catch {
        $exception = $_.Exception
        while ($exception.InnerException) { $exception = $exception.InnerException }
        $code = $exception.HResult.ToString('X8')
        $message = switch ($code) {
            '80070005' { 'Weekly maintenance task cannot be read by this account. Run Repair to restore read access.' }
            '80070002' { 'Weekly maintenance task is missing. Run Repair to register it.' }
            default { "Weekly maintenance could not be checked ($code). Run Repair and review the log if it persists." }
        }
        return @{Status='FAIL'; Message=$message}
    }
}
