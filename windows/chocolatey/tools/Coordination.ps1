# SDE_COORDINATION_V1
# Shared with the Rust GUI/updater. These leases confer no privilege or command rights.
$script:SkyviewCoordinationRoot = 'C:\ProgramData\SkyviewRoboticsCoordination'
function Assert-SkyviewProtectedPath([string]$Path, [switch]$Gate, [switch]$Anchor) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Untrusted SDE coordination link.' }
    $acl = Get-Acl -LiteralPath $Path
    $owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
    if ($owner -notin @('S-1-5-18','S-1-5-32-544') -and (-not $Anchor -or $owner -ne 'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')) { throw 'Untrusted SDE coordination owner.' }
    foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -ne 'Allow' -or ($Anchor -and ($rule.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly))) { continue }
        $write = [Security.AccessControl.FileSystemRights]::Write -bor [Security.AccessControl.FileSystemRights]::Delete -bor [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor [Security.AccessControl.FileSystemRights]::ChangePermissions -bor [Security.AccessControl.FileSystemRights]::TakeOwnership
        if ($Anchor) { $write = [Security.AccessControl.FileSystemRights]::Delete -bor [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor [Security.AccessControl.FileSystemRights]::ChangePermissions -bor [Security.AccessControl.FileSystemRights]::TakeOwnership }
        if (($rule.FileSystemRights -band $write) -ne 0 -and $rule.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544') -and (-not $Anchor -or $rule.IdentityReference.Value -ne 'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')) {
            throw 'Untrusted SDE coordination permissions.'
        }
    }
    if ($Gate -and ($item.PSIsContainer -or $item.Length -ne 0)) { throw 'Invalid SDE coordination gate.' }
    if (-not $Gate -and -not $item.PSIsContainer) { throw 'Invalid SDE coordination directory.' }
}
function Invoke-SkyviewNativeMaintenanceProcess {
    param([string[]]$Arguments, [switch]$Capture)
    # Explicit process pipes also work with the installed GUI-subsystem binary.
    # Drain both streams concurrently, without buffering package logs or killing
    # installers to enforce a timeout. No Invoke-Expression or shell command text.
    $application = 'C:\Program Files\Skyview Dev Setup\skyview-dev-setup.exe'
    $quoted = foreach ($argument in $Arguments) {
        '"' + (($argument -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
    }
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $application
    $start.Arguments = $quoted -join ' '
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.StandardOutputEncoding = New-Object Text.UTF8Encoding($false)
    $start.StandardErrorEncoding = New-Object Text.UTF8Encoding($false)
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    $captured = New-Object Text.StringBuilder
    try {
        if (-not $process.Start()) { throw 'SDE maintenance supervisor could not start.' }
        $stdout = $process.StandardOutput.ReadLineAsync()
        $stderr = $process.StandardError.ReadLineAsync()
        while ($null -ne $stdout -or $null -ne $stderr) {
            $progress = $false
            if ($null -ne $stdout -and $stdout.IsCompleted) {
                $line = $stdout.GetAwaiter().GetResult()
                if ($null -eq $line) { $stdout = $null }
                else {
                    if ($Capture) {
                        if ($captured.Length + $line.Length -gt 1024) { throw 'Invalid supervisor capability response.' }
                        [void]$captured.AppendLine($line)
                    } else { Write-Host $line }
                    $stdout = $process.StandardOutput.ReadLineAsync()
                }
                $progress = $true
            }
            if ($null -ne $stderr -and $stderr.IsCompleted) {
                $line = $stderr.GetAwaiter().GetResult()
                if ($null -eq $line) { $stderr = $null }
                else { Write-Host $line; $stderr = $process.StandardError.ReadLineAsync() }
                $progress = $true
            }
            if (-not $progress) { Start-Sleep -Milliseconds 20 }
        }
        $process.WaitForExit()
        [pscustomobject]@{ExitCode=$process.ExitCode;Output=$captured.ToString()}
    } finally { $process.Dispose() }
}
function Invoke-SkyviewCoordinated {
    param([scriptblock]$Action, [switch]$Mutation, [switch]$ReadOnly,
          [string]$EntryPoint, [string[]]$EntryArguments=@())
    if ($Mutation -and $ReadOnly) { throw 'A changing operation cannot use read-only coordination.' }
    $root = $script:SkyviewCoordinationRoot
    Assert-SkyviewProtectedPath 'C:\' -Anchor
    Assert-SkyviewProtectedPath 'C:\ProgramData' -Anchor
    Assert-SkyviewProtectedPath $root
    $journal = Join-Path $root 'transaction.json'
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    $administrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($global:SkyviewOperationLease -is [IO.FileStream] -and
        -not $global:SkyviewOperationLease.SafeFileHandle.IsClosed -and
        $global:SkyviewOperationLease.Name -eq (Join-Path $root 'operations.gate')) {
        & $Action
        return
    }
    # Nested Chocolatey configuration runs in another elevated process. Only the
    # private root-owned journal can authorize reuse of the supervising transaction.
    # Presence/state never authorizes a new privileged operation or a caller path.
    if ($administrator -and $env:SKYVIEW_TRANSACTION_TOKEN) {
        $record = Get-Content -LiteralPath $journal -Raw -ErrorAction Stop | ConvertFrom-Json
        if ($record.schema -ne 1 -or $record.token -cne $env:SKYVIEW_TRANSACTION_TOKEN) { throw 'Invalid inherited SDE transaction.' }
        $held = $false
        try {
            $probe = [IO.File]::Open((Join-Path $root 'operations.gate'), 'Open', 'Read', 'Read')
            $probe.Dispose()
        } catch [IO.IOException] {
            if (($_.Exception.HResult -band 0xffff) -ne 32) { throw }
            $held = $true
        }
        if (-not $held) { throw 'The supervising SDE transaction was interrupted; mentor review is required.' }
        & $Action
        return
    }
    if ($Mutation -and $EntryPoint) {
        if (-not $administrator) { throw 'System operations require administrator authentication.' }
        $nativeSession = $null
        try {
            # Keep coordinated application replacement out of capability/launch
            # negotiation. This is only a shared lease, never mutation authority.
            Assert-SkyviewProtectedPath (Join-Path $root 'sessions.gate') -Gate
            $nativeSession = [IO.File]::Open((Join-Path $root 'sessions.gate'),'Open','Read','Read')
            # Older installed apps understand this safe non-GUI mode, but return
            # no capability. Never send an unknown flag to an older app.
            $capability = Invoke-SkyviewNativeMaintenanceProcess -Arguments @('--coordination-init') -Capture
            if ($capability.ExitCode -ne 0 -or $capability.Output.Trim() -cne 'SDE_WINDOWS_MAINTENANCE_SUPERVISOR_V1') {
                throw 'Install or repair the SDE application to enable compatible maintenance supervision.'
            }
            $result = Invoke-SkyviewNativeMaintenanceProcess -Arguments (@('--supervise-windows-maintenance',[IO.Path]::GetFullPath($EntryPoint)) + $EntryArguments)
            # Reexecute once, never replay $Action or clear the native journal.
            exit $result.ExitCode
        } catch [IO.IOException] {
            if (($_.Exception.HResult -band 0xffff) -eq 32) { exit 75 }
            throw
        } finally { if ($nativeSession) { $nativeSession.Dispose() } }
    }
    $session = $null; $operation = $null; $ownedJournal = $false
    $previousToken = $env:SKYVIEW_TRANSACTION_TOKEN
    $previousLease = $global:SkyviewOperationLease
    try {
        Assert-SkyviewProtectedPath (Join-Path $root 'sessions.gate') -Gate
        $session = [IO.File]::Open((Join-Path $root 'sessions.gate'), 'Open', 'Read', 'Read')
        Assert-SkyviewProtectedPath (Join-Path $root 'operations.gate') -Gate
        $operation = [IO.File]::Open((Join-Path $root 'operations.gate'), 'Open', 'Read', 'None')
        if (Test-Path -LiteralPath $journal) {
            if (-not $ReadOnly) { throw 'An interrupted system operation needs mentor review before another change.' }
            # Validation must remain available for diagnosis. Keep the exclusive
            # operation gate, never read/clear the private journal, and retain the
            # interruption as a warning rather than treating validation as recovery.
            Write-Host 'SKYVIEW_EVENT|validation|WARNING|An interrupted system operation still needs mentor review before another change.'
        }
        if ($Mutation) {
            if (-not $administrator) { throw 'System operations require administrator authentication.' }
            $env:SKYVIEW_TRANSACTION_TOKEN = [guid]::NewGuid().ToString()
            $record = @{schema=1;token=$env:SKYVIEW_TRANSACTION_TOKEN;pid=$PID;kind='system'} | ConvertTo-Json -Compress
            # Create with a private DACL atomically, before any package action.
            $security = New-Object Security.AccessControl.FileSecurity
            $security.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)')
            $file = New-Object IO.FileStream($journal,[IO.FileMode]::CreateNew,[Security.AccessControl.FileSystemRights]::Write,[IO.FileShare]::None,4096,[IO.FileOptions]::WriteThrough,$security)
            try {
                $bytes = [Text.Encoding]::UTF8.GetBytes($record)
                $file.Write($bytes,0,$bytes.Length); $file.Flush($true)
            } finally { $file.Dispose() }
            $ownedJournal = $true
        }
        $global:SkyviewOperationLease = $operation
        & $Action
        # Only a normally completed script clears the record. A thrown exception,
        # crash, cancellation or reboot retains it; no package child is killed.
        if ($ownedJournal) { Remove-Item -LiteralPath $journal -Force }
    } catch [IO.IOException] {
        if (($_.Exception.HResult -band 0xffff) -eq 32) { throw 'SKYVIEW_DEFERRED' }
        throw
    } finally {
        $env:SKYVIEW_TRANSACTION_TOKEN = $previousToken
        $global:SkyviewOperationLease = $previousLease
        if ($operation) { $operation.Dispose() }
        if ($session) { $session.Dispose() }
    }
}
