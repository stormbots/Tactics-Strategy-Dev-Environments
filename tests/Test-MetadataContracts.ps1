$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/ToolRecords.ps1')
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/Inspect-SkyviewSchedule.ps1')
function Assert($Condition, $Message) { if (-not $Condition) { throw $Message } }
# Shadow Chocolatey with fixture data: no queries, installs, or system changes.
function choco {
    $global:LASTEXITCODE = 0
    switch ($args[0]) {
        'list' { 'git|2.43.0'; 'nodejs-lts|24.20.0'; 'python314|3.14.7' }
        'outdated' {
            if ($script:FeedFailure) { $global:LASTEXITCODE=1; return }
            'git|2.43.0|2.44.0|false'; 'nodejs-lts|24.20.0|26.0.0|true'; 'python314|3.14.7|3.15.0|false'
        }
        'search' { 'nodejs-lts|26.0.0'; 'nodejs-lts|24.21.0'; 'nodejs-lts|24.20.0' }
    }
}
$installed = @{Git='2.43.0'; 'Node.js'='24.20.0'; Python='3.14.7'; Chrome='144.0'; Firefox='144.0'}
$records = @(Get-SkyviewToolRecords -Installed $installed -CheckUpdates $true)
$git = $records | Where-Object tool -eq Git
$node = $records | Where-Object tool -eq Node.js
Assert ($git.updateAvailable -and $git.availableVersion -eq '2.44.0') 'Git update missing.'
Assert ($node.updateAvailable -and $node.availableVersion -eq '24.21.0') 'Pinned Node family update missing.'
Assert (-not ($records | Where-Object tool -eq Python).updateAvailable) 'Python runtime boundary violated.'
Assert (($records | Where-Object tool -eq Chrome).updateCheck -eq 'native') 'Chrome must use native updates.'
Assert (($records | Where-Object tool -eq Firefox).updateCheck -eq 'unavailable') 'Untracked tool incorrectly reported current.'
$script:FeedFailure = $true
$records = @(Get-SkyviewToolRecords -Installed $installed -CheckUpdates $true)
Assert (($records | Where-Object tool -eq Git).updateCheck -eq 'unavailable') 'Feed failure incorrectly reported no updates.'
Assert (-not ($records | Where-Object tool -eq Git).updateAvailable) 'Failed query emitted a candidate.'
Assert ((@(Get-SkyviewToolRecords -Installed $installed -CheckUpdates $false) | Where-Object tool -eq Git).updateCheck -eq 'notChecked') 'Skipped query incorrectly reported current.'
Remove-Item Function:choco

$xml = '<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><Triggers><CalendarTrigger><StartBoundary>2026-10-04T03:00:00</StartBoundary><Enabled>true</Enabled><ScheduleByWeek><WeeksInterval>1</WeeksInterval><DaysOfWeek><Sunday /></DaysOfWeek></ScheduleByWeek></CalendarTrigger></Triggers><Settings><StartWhenAvailable>true</StartWhenAvailable></Settings></Task>'
$task = [pscustomobject]@{ Xml=$xml; Enabled=$true; State=3; LastRunTime=[datetime]'1899-12-30'; NextRunTime=[datetime]'2026-10-11T03:00:00'; LastTaskResult=267011 }
$result = ConvertTo-SkyviewSchedule -Task $task
Assert ($result.status -eq 'enabled' -and $result.lastResult -eq 'never') 'Never-run task incorrectly reported success.'
Assert ($result.catchUp -and $result.frequency -like '*Sunday at 03:00*') 'Actual trigger/settings not inspected.'
$task.Enabled = $false
$task.LastRunTime = [datetime]'2026-10-04T03:00:00'
$task.LastTaskResult = 1
$result = ConvertTo-SkyviewSchedule -Task $task
Assert ($result.status -eq 'disabled' -and $null -eq $result.nextRun -and $result.lastResult -eq 'failure') 'Disabled/failed schedule not represented correctly.'
$task.Enabled = $true; $task.State = 4
Assert ((ConvertTo-SkyviewSchedule -Task $task).lastResult -eq 'running') 'Running state lost.'
$task.State = 3; $task.LastTaskResult = 0; $task.Xml = $xml.Replace('<Enabled>true</Enabled>', '<Enabled>false</Enabled>')
Assert ($null -eq (ConvertTo-SkyviewSchedule -Task $task).nextRun) 'Disabled trigger advertised a next run.'
# COM error fixtures cover the native read-only command's actionable states.
function New-Object { throw [Runtime.InteropServices.COMException]::new('Denied', [int]-2147024891) }
$result = Get-SkyviewSchedule
Assert ($result.status -eq 'unavailable' -and $result.note -like '*cannot read*') 'Read permission error not explained.'
Remove-Item Function:New-Object
function New-Object { throw [Runtime.InteropServices.COMException]::new('Missing', [int]-2147024893) }
Assert ((Get-SkyviewSchedule).status -eq 'missing') 'Missing task incorrectly reported as success.'
Remove-Item Function:New-Object
Write-Host 'SKYVIEW_METADATA_CONTRACTS_OK'
