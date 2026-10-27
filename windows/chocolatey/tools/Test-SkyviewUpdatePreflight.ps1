# Read-only preflight for GUI Install and Update. No package or policy changes.
[CmdletBinding()]
param([ValidateSet('install','update')][string]$Operation='update')
$ErrorActionPreference = 'Stop'
$rows = New-Object 'System.Collections.Generic.List[object]'
function Add-Check($Name,$Status,$Detail) { $rows.Add([pscustomobject]@{name=$Name;status=$Status;detail=$Detail}) }
$systemRequired=if ($Operation -eq 'install') { 8GB } else { 3GB }
$userRequired=if ($Operation -eq 'install') { 1GB } else { 512MB }
foreach ($volume in @(@{Path='C:\';Required=$systemRequired;Name='System disk'},@{Path=$env:USERPROFILE;Required=$userRequired;Name='User disk'})) {
    try {
        $drive=New-Object -TypeName IO.DriveInfo -ArgumentList ([IO.Path]::GetPathRoot($volume.Path))
        $free=$drive.AvailableFreeSpace
        $state=if ($free -ge $volume.Required) {'pass'} else {'blocking'}
        Add-Check $volume.Name $state ("Required free: {0} MiB; available: {1} MiB. Actual download sizes can vary." -f ($volume.Required/1MB),[math]::Floor($free/1MB))
    } catch { Add-Check $volume.Name unavailable 'Free space could not be read. Ask a mentor if disk space is uncertain.' }
}
try {
    $active=@(Get-CimInstance Win32_Process -Filter "Name = 'choco.exe' OR Name = 'msiexec.exe'" | Where-Object {
        $_.Name -eq 'msiexec.exe' -or -not $_.CommandLine -or $_.CommandLine -notmatch '(?i)choco(?:\.exe)?"?\s+(list|outdated|search)(?:\s|$)'
    })
    if ($active.Count) { Add-Check 'Package manager' blocking 'Chocolatey or Windows Installer is active. Wait for it to finish; do not terminate it.' }
    else { Add-Check 'Package manager' pass 'No Chocolatey or Windows Installer process was detected. Native installers still check their own transaction locks.' }
} catch { Add-Check 'Package manager' unavailable 'Package activity could not be inspected. Native installer checks still apply.' }
try {
    $restart=(Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') -or (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')
    if ($restart) { Add-Check Restart warning 'Windows reports a pending restart. Save work and arrange a restart before updating.' }
    else { Add-Check Restart pass 'No checked pending-restart marker was found; detection is not exhaustive.' }
} catch { Add-Check Restart unavailable 'Pending restart information could not be read.' }
foreach ($source in @(@{Name='Chocolatey packages';Url='https://community.chocolatey.org/api/v2/'},@{Name='Editor extensions';Url='https://open-vsx.org/api/-/query?size=1'})) {
    try {
        $null=Invoke-WebRequest -Uri $source.Url -Method Head -UseBasicParsing -TimeoutSec 4
        Add-Check $source.Name pass 'Source responded. Individual package downloads and vendor CDNs may still fail later.'
    } catch { Add-Check $source.Name unavailable 'Source availability could not be confirmed. Check the connection and retry; continuing may fail during downloads.' }
}
ConvertTo-Json -InputObject @($rows.ToArray()) -Compress
