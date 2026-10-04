$ErrorActionPreference = 'SilentlyContinue'
Unregister-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates' -Confirm:$false
Write-Host 'Removed the Skyview automatic-update scheduled task.'
Write-Host 'Dependency applications and developer settings are intentionally left installed.'
