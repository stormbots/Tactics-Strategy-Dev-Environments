# Read-only Python verification. No PATH edits, package changes or project execution.
# The scripts and arguments below are fixed; discovered paths are never shell text.
$script:SkyviewPythonIdentity = 'import json,sys; print(json.dumps({"version":"%d.%d.%d" % sys.version_info[:3],"executable":sys.executable}))'
function Invoke-SkyviewPythonQuery {
    param([string]$Executable, [string[]]$Arguments, [int]$TimeoutMs)
    if ($TimeoutMs -le 0) { return @{ Code=-1; Text=''; Reason='timeout' } }
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $Executable
    $start.Arguments = (@($Arguments | ForEach-Object {
        '"' + (($_ -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
    }) -join ' ')
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    $clock = [Diagnostics.Stopwatch]::StartNew()
    try {
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutMs)) {
            # Only this fixed read-only probe, never an installer/package child.
            $process.Kill()
            return @{ Code=-1; Text=''; Reason='timeout' }
        }
        $remaining = [Math]::Max(0, $TimeoutMs - [int]$clock.ElapsedMilliseconds)
        if (-not [Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($stdout,$stderr), $remaining)) {
            return @{ Code=-1; Text=''; Reason='timeout' }
        }
        $text = $stdout.GetAwaiter().GetResult()
        if ($text.Length -gt 16384) { return @{ Code=-1; Text=''; Reason='invalidOutput' } }
        return @{ Code=$process.ExitCode; Text=$text.Trim(); Reason='completed' }
    } catch { return @{ Code=-1; Text=''; Reason='unavailable' } }
    finally { $process.Dispose() }
}
function Get-SkyviewPythonCandidates {
    $paths = New-Object 'System.Collections.Generic.List[string]'
    $complete = $true
    # PEP 514 PythonCore records cover normal per-user and machine installations,
    # including nonstandard folders. Read both views without changing registration.
    foreach ($hive in @([Microsoft.Win32.RegistryHive]::CurrentUser,[Microsoft.Win32.RegistryHive]::LocalMachine)) {
        foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64,[Microsoft.Win32.RegistryView]::Registry32)) {
            $base = $null; $core = $null
            try {
                $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($hive,$view)
                $core = $base.OpenSubKey('Software\Python\PythonCore')
                if (-not $core) { continue }
                $tags = @($core.GetSubKeyNames())
                if ($tags.Count -gt 64) { $complete = $false }
                foreach ($tag in @($tags | Select-Object -First 64 | Where-Object { $_ -match '^3\.14(?:-\d+)?$' })) {
                    $key = $null
                    try {
                        $key = $core.OpenSubKey("$tag\InstallPath")
                        if (-not $key) { $complete = $false; continue }
                        $path = [string]$key.GetValue('ExecutablePath')
                        if (-not $path) {
                            $directory = [string]$key.GetValue('')
                            if ($directory) { $path = Join-Path $directory 'python.exe' }
                        }
                        if ($path) { $paths.Add($path) } else { $complete = $false }
                    } finally { if ($key) { $key.Dispose() } }
                }
            } catch { $complete = $false }
            finally {
                if ($core) { $core.Dispose() }
                if ($base) { $base.Dispose() }
            }
        }
    }
    $requiredPaths = @($paths | Select-Object -Unique)
    $default = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($default) { $paths.Add($default.Source) }
    $unique = @($paths | Select-Object -Unique)
    if ($unique.Count -gt 8) { $complete = $false }
    return [pscustomobject]@{ Paths=@($unique | Select-Object -First 8); RequiredPaths=$requiredPaths; Complete=$complete }
}
function Test-SkyviewPythonExecutable([string]$Path) {
    # Restrict execution to an explicit local executable, not aliases or command text.
    if (-not $Path -or $Path.Length -gt 4096 -or $Path -match '[\x00-\x1f|]' -or
        $Path -notmatch '^[A-Za-z]:\\' -or $Path -notmatch '(?i)\.exe$') { return $false }
    # Zero-length Windows execution aliases can open the Store, not run Python.
    try {
        $item = Get-Item -LiteralPath $Path -ErrorAction Stop
        return -not $item.PSIsContainer -and $item.Length -gt 0
    }
    catch { return $false }
}
function Get-SkyviewPythonRuntime {
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $record = [ordered]@{
        schema=1; component='Python'; requiredFamily='3.14'; status='notFound'
        reason='notDiscovered'; version=$null; executable=$null; pipVersion=$null
    }
    $candidates = Get-SkyviewPythonCandidates
    $incomplete = -not $candidates.Complete
    $unusable = $false
    $paths = New-Object 'System.Collections.Generic.List[string]'
    # List launcher registrations only. Asking a newer install manager to run
    # a missing family could offer/install it; discovery must never do that.
    $launcher = Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($launcher) {
        $query = Invoke-SkyviewPythonQuery $launcher.Source @('-0p') 2500
        if ($query.Code -eq 0) {
            $listed = $false
            foreach ($line in @($query.Text -split '[\r\n]+')) {
                if ($line -match '^\s*-(?:V:)?3\.14(?:-(?:32|64))?\s+\*?\s*(?<path>[A-Za-z]:\\.+\.exe)\s*$') {
                    $listed = $true
                    $listedPath = $Matches.path.Trim()
                    if (Test-SkyviewPythonExecutable $listedPath) { $paths.Add($listedPath) }
                    else { $incomplete = $true }
                }
            }
            # Listing no usable family is not proof that every possible install
            # is absent. Registry/PATH discovery can still supply a passing one.
            if (-not $listed) { $incomplete = $true }
        } else { $incomplete = $true }
    }
    foreach ($path in $candidates.Paths) { $paths.Add($path) }
    foreach ($path in @($paths | Select-Object -Unique)) {
        if ($clock.ElapsedMilliseconds -ge 12000) { $incomplete = $true; break }
        if (-not (Test-SkyviewPythonExecutable $path)) { $incomplete = $true; continue }
        $remaining = [Math]::Min(2500, 12000 - [int]$clock.ElapsedMilliseconds)
        $query = Invoke-SkyviewPythonQuery $path @('-I','-B','-c',$script:SkyviewPythonIdentity) $remaining
        if ($query.Code -ne 0) {
            if ($query.Reason -ne 'timeout' -and $candidates.RequiredPaths -contains $path) { $unusable = $true }
            else { $incomplete = $true }
            continue
        }
        try { $identity = $query.Text | ConvertFrom-Json -ErrorAction Stop }
        catch { $incomplete = $true; continue }
        if ($identity.version -isnot [string] -or $identity.executable -isnot [string] -or $identity.version -notmatch '\A\d{1,8}\.\d{1,8}\.\d{1,8}\z') { $incomplete = $true; continue }
        if ($identity.version -notmatch '^3\.14\.') {
            if ($candidates.RequiredPaths -contains $path) { $unusable = $true }
            continue
        }
        # Resolve once more to the actual interpreter reported by the candidate.
        # Verify that exact executable before using it for pip (shims cannot mix pairs).
        $selected = [string]$identity.executable
        if (-not (Test-SkyviewPythonExecutable $selected)) { $unusable = $true; continue }
        $remaining = [Math]::Min(2500, 12000 - [int]$clock.ElapsedMilliseconds)
        $actual = Invoke-SkyviewPythonQuery $selected @('-I','-B','-c',$script:SkyviewPythonIdentity) $remaining
        if ($actual.Reason -eq 'timeout') { $incomplete=$true; continue }
        try { $verified = $actual.Text | ConvertFrom-Json -ErrorAction Stop }
        catch { $unusable = $true; continue }
        if ($actual.Code -ne 0 -or $verified.version -isnot [string] -or $verified.executable -isnot [string] -or $verified.version -notmatch '\A3\.14\.\d{1,8}\z' -or
            -not [string]::Equals($selected,[string]$verified.executable,[StringComparison]::OrdinalIgnoreCase)) {
            $unusable = $true; continue
        }
        $remaining = [Math]::Min(2500, 12000 - [int]$clock.ElapsedMilliseconds)
        $pip = Invoke-SkyviewPythonQuery $selected @('-I','-B','-m','pip','--version') $remaining
        if ($pip.Code -eq 0 -and $pip.Text -match '\Apip (\d{1,8}(?:\.\d{1,8}){1,3}) .+ \(python 3\.14\)\z') {
            $record.status='passed'; $record.reason='verified'
            $record.version=$verified.version; $record.executable=$selected; $record.pipVersion=$Matches[1]
            return [pscustomobject]$record
        }
        $record.version=$verified.version; $record.executable=$selected
        if ($pip.Reason -eq 'timeout') { $incomplete=$true; $record.reason='pipTimeout' }
        else { $unusable=$true; $record.reason='pipFailed' }
    }
    if ($record.reason -eq 'pipTimeout') { $record.status='incomplete' }
    elseif ($unusable) { $record.status='unusable'; if ($record.reason -eq 'notDiscovered') { $record.reason='interpreterFailed' } }
    elseif ($incomplete) { $record.status='incomplete'; if ($record.reason -eq 'notDiscovered') { $record.reason='discoveryIncomplete' } }
    return [pscustomobject]$record
}
