param([ValidateSet('all','boot')][string]$Mode='all')
# Compiled into the fixed read-only diagnostic. No caller paths, no remote CIM,
# no package/registry mutation, no process termination, and no event-log changes.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$result = @{schema=1;activity='unknown';health='unknown';activityReason='unavailable';healthReason='unavailable';bootKey=$null;diagnostics=@()}
$startup = $null
$session = $null
try {
    $event = Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-Kernel-General';Id=12} -MaxEvents 1 -ErrorAction Stop
    if ($event.Id -eq 12 -and $event.ProviderName -ceq 'Microsoft-Windows-Kernel-General' -and $event.RecordId -gt 0 -and $event.TimeCreated) {
        $ticks = $event.TimeCreated.ToUniversalTime().Ticks
        if ($ticks -gt 0) {
            $startup = $event.RecordId.ToString([Globalization.CultureInfo]::InvariantCulture) + ':' + $ticks.ToString([Globalization.CultureInfo]::InvariantCulture)
        }
    }
} catch { $startup = $null; $result.diagnostics += @{source='boot_event';code=[long]$_.Exception.HResult} }
try {
    $filter = "Name = 'smss.exe' AND ParentProcessId = 4"
    if ($Mode -eq 'all') { $filter = "($filter) OR Name = 'choco.exe' OR Name = 'msiexec.exe' OR Name = 'winget.exe' OR Name = 'dism.exe'" }
    $processes = @(Get-CimInstance -ClassName Win32_Process -OperationTimeoutSec 3 -Filter $filter -ErrorAction Stop)
    $primary = @($processes | Where-Object { $_.Name -ieq 'smss.exe' -and $_.ParentProcessId -eq 4 -and $_.SessionId -eq 0 })
    if ($primary.Count -eq 1 -and $primary[0].ProcessId -gt 0 -and $primary[0].CreationDate) {
        $created = $primary[0].CreationDate.ToUniversalTime().Ticks
        if ($created -gt 0) {
            $session = $primary[0].ProcessId.ToString([Globalization.CultureInfo]::InvariantCulture) + ':' + $created.ToString([Globalization.CultureInfo]::InvariantCulture)
        }
    }
    if ($Mode -eq 'all') {
        $active = @($processes | Where-Object {
            $_.Name -ine 'smss.exe' -and -not ($_.Name -ieq 'choco.exe' -and $_.CommandLine -and
                $_.CommandLine -match '(?i)choco(?:\.exe)?"?\s+(list|outdated|search)(?:\s|$)')
        })
        if ($active.Count) { $result.activity='active'; $result.activityReason='package_active' }
        else { $result.activity='inactive'; $result.activityReason='no_package_activity' }
    }
} catch { $session = $null; $result.activity='unknown'; $result.activityReason='unavailable'; $result.diagnostics += @{source='package_activity';code=[long]$_.Exception.HResult} }
if (-not $session) { $result.diagnostics += @{source='session_identity';code=$null} }
if ($session -and $startup) { $result.bootKey = 'windows-session-start:' + $session + ':' + $startup }
if ($Mode -eq 'all') {
    try {
        if (Test-Path -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\InProgress' -ErrorAction Stop) {
            $result.health='incomplete'; $result.healthReason='package_incomplete'
        } else {
            # Absence of this marker is not a complete Windows package audit.
            # Unknown health warns when activity is established inactive.
            $result.health='unknown'; $result.healthReason='unavailable'
        }
    } catch { $result.health='unknown'; $result.healthReason='unavailable'; $result.diagnostics += @{source='package_health';code=[long]$_.Exception.HResult} }
}
[Console]::Write(($result | ConvertTo-Json -Compress -Depth 4))
