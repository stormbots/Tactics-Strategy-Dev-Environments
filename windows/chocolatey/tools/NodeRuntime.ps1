# Read-only selection. Loading this file performs no provisioning or manager switch.
function Invoke-SkyviewNodeQuery {
    param([string]$Executable, [string[]]$Arguments, [int]$TimeoutMs)
    if ($TimeoutMs -le 0) { return @{ Code=-1; Text=''; Reason='timeout' } }
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $Executable
    $start.Arguments = (@($Arguments | ForEach-Object {
        '"' + (($_ -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
    }) -join ' ')
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.WorkingDirectory = [IO.Path]::GetTempPath()
    foreach ($key in @('NODE_OPTIONS','NODE_PATH','NODE_COMPILE_CACHE','NODE_V8_COVERAGE')) {
        $start.EnvironmentVariables.Remove($key)
    }
    $start.EnvironmentVariables['npm_config_update_notifier']='false'
    $start.EnvironmentVariables['npm_config_ignore_scripts']='true'
    $start.EnvironmentVariables['npm_config_audit']='false'
    $start.EnvironmentVariables['npm_config_fund']='false'
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
function Test-SkyviewNodeExecutable([string]$Path) {
    if (-not $Path -or $Path.Length -gt 4096 -or $Path -match '[\x00-\x1f|]' -or
        $Path -notmatch '^[A-Za-z]:\\' -or $Path -notmatch '(?i)\.exe$') { return $false }
    try {
        $item=Get-Item -LiteralPath $Path -ErrorAction Stop
        return -not $item.PSIsContainer -and $item.Length -gt 0
    } catch { return $false }
}
function Get-SkyviewNodeCandidates {
    $paths=New-Object 'System.Collections.Generic.List[string]'
    $required=New-Object 'System.Collections.Generic.List[string]'
    $complete=$true
    # Known per-user version stores only. Never invoke a manager or scan a drive.
    $stores=@()
    if ($env:NVM_HOME) { $stores+=@{Root=$env:NVM_HOME;Child='node.exe'} }
    elseif ($env:APPDATA) { $stores+=@{Root=(Join-Path $env:APPDATA 'nvm');Child='node.exe'} }
    $voltaRoot=if ($env:VOLTA_HOME) { $env:VOLTA_HOME } elseif ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'Volta' }
    if ($voltaRoot) { $stores+=@{Root=(Join-Path $voltaRoot 'tools\image\node');Child='node.exe'} }
    $fnmRoots=@($env:FNM_DIR)
    if (-not $env:FNM_DIR) {
        foreach ($parent in @($env:APPDATA,$env:LOCALAPPDATA)) { if ($parent) { $fnmRoots+=Join-Path $parent 'fnm' } }
    }
    foreach ($fnmRoot in $fnmRoots) {
        if ($fnmRoot) { $stores+=@{Root=(Join-Path $fnmRoot 'node-versions');Child='installation\node.exe'} }
    }
    foreach ($store in $stores) {
        try {
            if (-not (Test-Path -LiteralPath $store.Root -ErrorAction Stop)) { continue }
            $versions=@(Get-ChildItem -LiteralPath $store.Root -Directory -ErrorAction Stop |
                Where-Object { $_.Name -match '\Av?24\.\d+\.\d+\z' } |
                Sort-Object { [version]($_.Name -replace '^v','') } -Descending)
            if ($versions.Count -gt 8) { $complete=$false }
            foreach ($version in @($versions | Select-Object -First 8)) {
                $path=Join-Path $version.FullName $store.Child
                $paths.Add($path); $required.Add($path)
            }
        } catch { $complete=$false }
    }
    foreach ($key in @('HKCU:\SOFTWARE\Node.js','HKLM:\SOFTWARE\Node.js','HKLM:\SOFTWARE\WOW6432Node\Node.js')) {
        try {
            if (Test-Path -LiteralPath $key -ErrorAction Stop) {
                $location=(Get-ItemProperty -LiteralPath $key -ErrorAction Stop).InstallPath
                if ($location) { $paths.Add((Join-Path $location 'node.exe')) } else { $complete=$false }
            }
        } catch { $complete=$false }
    }
    foreach ($branch in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall')) {
        try {
            if (-not (Test-Path -LiteralPath $branch -ErrorAction Stop)) { continue }
            $keys=@(Get-ChildItem -LiteralPath $branch -ErrorAction Stop)
            if ($keys.Count -gt 512) { $complete=$false }
            foreach ($key in @($keys | Select-Object -First 512)) {
                $entry=Get-ItemProperty -LiteralPath $key.PSPath -ErrorAction Stop
                if ($entry.DisplayName -eq 'Node.js') {
                    if ($entry.InstallLocation) { $paths.Add((Join-Path $entry.InstallLocation 'node.exe')) }
                    else { $complete=$false }
                }
            }
        } catch { $complete=$false }
    }
    foreach ($parent in @($env:ProgramFiles,${env:ProgramFiles(x86)})) {
        if ($parent) {
            $path=Join-Path $parent 'nodejs\node.exe'
            if (Test-Path -LiteralPath $path -ErrorAction SilentlyContinue) { $paths.Add($path) }
        }
    }
    if ($env:NVM_SYMLINK) {
        $path=Join-Path $env:NVM_SYMLINK 'node.exe'
        if (Test-Path -LiteralPath $path -ErrorAction SilentlyContinue) { $paths.Add($path) }
    }
    $default=Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($default) {
        $voltaBin=if ($voltaRoot) { (Join-Path $voltaRoot 'bin') + '\' } else { '' }
        if ($voltaBin -and $default.Source.StartsWith($voltaBin,[StringComparison]::OrdinalIgnoreCase)) {
            # A Volta launcher can acquire a missing runtime. Use only its
            # cached version store above; discovery must not request downloads.
            $complete=$false
        } else { $paths.Add($default.Source) }
    }
    else {
        # Shell shims are not executed as discovery commands. Supported stores
        # above may still supply the actual interpreter; otherwise keep unknown.
        if (Get-Command node -ErrorAction SilentlyContinue) { $complete=$false }
    }
    $unique=@($paths | Select-Object -Unique)
    if ($unique.Count -gt 12) { $complete=$false }
    return [pscustomobject]@{Paths=@($unique | Select-Object -First 12);RequiredPaths=@($required);Complete=$complete}
}
function Get-SkyviewNodeRuntime {
    $clock=[Diagnostics.Stopwatch]::StartNew()
    $record=[ordered]@{schema=1;component='Node.js';requiredFamily='24';status='notFound';reason='notDiscovered';version=$null;executable=$null;npmVersion=$null;npmCli=$null;maintenanceEligibility='notEvaluated'}
    $candidates=Get-SkyviewNodeCandidates
    $incomplete=-not $candidates.Complete
    $unusable=$false
    $probe=Join-Path $PSScriptRoot 'NodeRuntimeProbe.cjs'
    foreach ($path in $candidates.Paths) {
        if ($clock.ElapsedMilliseconds -ge 15000) { $incomplete=$true; break }
        if (-not (Test-SkyviewNodeExecutable $path)) { $incomplete=$true; continue }
        $remaining=[Math]::Min(2500,15000-[int]$clock.ElapsedMilliseconds)
        $query=Invoke-SkyviewNodeQuery $path @($probe,'identity') $remaining
        if ($query.Code -ne 0) {
            if ($query.Reason -eq 'timeout' -or $candidates.RequiredPaths -notcontains $path) { $incomplete=$true }
            else { $unusable=$true }
            continue
        }
        try { $identity=$query.Text | ConvertFrom-Json -ErrorAction Stop }
        catch { $incomplete=$true; continue }
        if ($identity.version -isnot [string] -or $identity.version -notmatch '\A\d{1,8}\.\d{1,8}\.\d{1,8}\z') { $incomplete=$true; continue }
        if ($identity.version -notmatch '^24\.') {
            if ($candidates.RequiredPaths -contains $path) { $unusable=$true }
            continue
        }
        $selected=[string]$identity.executable
        if (-not (Test-SkyviewNodeExecutable $selected)) { $unusable=$true; continue }
        $remaining=[Math]::Min(2500,15000-[int]$clock.ElapsedMilliseconds)
        $actual=Invoke-SkyviewNodeQuery $selected @($probe,'identity') $remaining
        if ($actual.Reason -eq 'timeout') { $incomplete=$true; continue }
        try { $verified=$actual.Text | ConvertFrom-Json -ErrorAction Stop }
        catch { $unusable=$true; continue }
        if ($actual.Code -ne 0 -or $verified.version -isnot [string] -or $verified.version -notmatch '\A24\.\d{1,8}\.\d{1,8}\z' -or
            -not [string]::Equals($selected,[string]$verified.executable,[StringComparison]::OrdinalIgnoreCase)) { $unusable=$true; continue }
        $record.version=$verified.version; $record.executable=$selected
        $remaining=[Math]::Min(2500,15000-[int]$clock.ElapsedMilliseconds)
        $pair=Invoke-SkyviewNodeQuery $selected @($probe,'npm') $remaining
        if ($pair.Reason -eq 'timeout') { $incomplete=$true; $record.reason='npmTimeout'; continue }
        try { $npm=$pair.Text | ConvertFrom-Json -ErrorAction Stop }
        catch { $unusable=$true; $record.reason='npmFailed'; continue }
        $expected=($selected -replace '[\\/][^\\/]+$','') + '\node_modules\npm\bin\npm-cli.js'
        if ($expected.Length -gt 4096) { $incomplete=$true; continue }
        if ($pair.Code -ne 0 -or $npm.version -ne $verified.version -or
            -not [string]::Equals($selected,[string]$npm.executable,[StringComparison]::OrdinalIgnoreCase) -or
            -not [string]::Equals($expected,[string]$npm.npmCli,[StringComparison]::OrdinalIgnoreCase) -or
            $npm.npmVersion -isnot [string] -or $npm.npmVersion -notmatch '\A[0-9][A-Za-z0-9.!+_-]{0,119}\z') { $unusable=$true; $record.reason='npmFailed'; continue }
        $remaining=[Math]::Min(2500,15000-[int]$clock.ElapsedMilliseconds)
        $version=Invoke-SkyviewNodeQuery $selected @($expected,'--version') $remaining
        if ($version.Code -eq 0 -and $version.Text -ceq $npm.npmVersion) {
            $record.status='passed';$record.reason='verified';$record.npmVersion=$npm.npmVersion;$record.npmCli=$expected
            return [pscustomobject]$record
        }
        if ($version.Reason -eq 'timeout') { $incomplete=$true;$record.reason='npmTimeout' }
        else { $unusable=$true;$record.reason='npmFailed' }
    }
    if ($record.reason -eq 'npmTimeout') { $record.status='incomplete' }
    elseif ($unusable) { $record.status='unusable';if ($record.reason -eq 'notDiscovered') { $record.reason='nodeFailed' } }
    elseif ($incomplete) { $record.status='incomplete';if ($record.reason -eq 'notDiscovered') { $record.reason='discoveryIncomplete' } }
    return [pscustomobject]$record
}
