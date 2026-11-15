# Read-only observations. Never apply recommendations or inspect project files.
function Test-SkyviewGitFile([string]$Path) {
    try {
        $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
        try { $null=$stream.ReadByte() } finally { $stream.Dispose() }
    } catch {
        $errorObject=$_.Exception
        if ($errorObject.InnerException) { $errorObject=$errorObject.InnerException }
        if ($errorObject -isnot [IO.FileNotFoundException] -and $errorObject -isnot [IO.DirectoryNotFoundException]) { return $false }
    }
    return $true
}
function Test-SkyviewGitSources([string]$Directory) {
    $sources=@()
    if ($null -ne [Environment]::GetEnvironmentVariable('GIT_CONFIG_GLOBAL','Process')) { $sources+= $env:GIT_CONFIG_GLOBAL }
    else {
        $profileHome=if ($env:HOME) { $env:HOME } elseif ($env:USERPROFILE) { $env:USERPROFILE } else { [Environment]::GetFolderPath('UserProfile') }
        $sources+=Join-Path $profileHome '.gitconfig'
        $xdg=if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } else { Join-Path $profileHome '.config' }
        $sources+=Join-Path $xdg 'git/config'
    }
    if ($env:GIT_CONFIG_SYSTEM -and $env:GIT_CONFIG_NOSYSTEM -notmatch '^(?i:1|true|yes|on)$') { $sources+=$env:GIT_CONFIG_SYSTEM }
    foreach ($source in $sources) {
        $path=if ([IO.Path]::IsPathRooted($source)) { $source } else { Join-Path $Directory $source }
        if (-not (Test-SkyviewGitFile $path)) { return $false }
    }
    return $true
}
function Test-SkyviewGitIncludes($Probe,[string]$Directory) {
    if ($Probe.Code -eq 1 -and $Probe.Text -eq '') { return $true }
    $fields=$Probe.Text.Split([char]0)
    if ($Probe.Code -ne 0 -or $fields[-1] -ne '' -or $fields.Count % 2 -ne 1 -or $fields.Count -gt 65) { return $false }
    for ($index=0;$index -lt $fields.Count-1;$index+=2) {
        $origin=$fields[$index];$value=$fields[$index+1]
        if (-not $origin.StartsWith('file:') -or -not $value -or $value -match '[\x00-\x1f]') { return $false }
        $path=$value
        if (-not [IO.Path]::IsPathRooted($path)) {
            $source=$origin.Substring(5)
            if (-not [IO.Path]::IsPathRooted($source)) { $source=Join-Path $Directory $source }
            $path=Join-Path ([IO.Path]::GetDirectoryName($source)) $path
        }
        if (-not (Test-SkyviewGitFile $path)) { return $false }
    }
    return $true
}
function Invoke-SkyviewGitQuery {
    param([string]$Executable,[string[]]$Arguments,[string]$Directory)
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$Executable
    $start.Arguments=(@($Arguments | ForEach-Object {
        '"' + (($_ -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
    }) -join ' ')
    $start.UseShellExecute=$false
    $start.CreateNoWindow=$true
    $start.WorkingDirectory=$Directory
    foreach ($key in @('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE','GIT_PREFIX')) {
        $start.EnvironmentVariables.Remove($key)
    }
    $start.RedirectStandardOutput=$true
    $start.RedirectStandardError=$true
    $start.StandardOutputEncoding=New-Object Text.UTF8Encoding($false)
    $start.StandardErrorEncoding=New-Object Text.UTF8Encoding($false)
    $process=New-Object Diagnostics.Process
    $process.StartInfo=$start
    $clock=[Diagnostics.Stopwatch]::StartNew()
    try {
        $null=$process.Start()
        $stdout=$process.StandardOutput.ReadToEndAsync()
        $stderr=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(3000)) {
            # Only our own fixed, read-only Git process; never package work.
            $process.Kill()
            return @{Code=-1;Text=''}
        }
        $remaining=[Math]::Max(0,3000-[int]$clock.ElapsedMilliseconds)
        if (-not [Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($stdout,$stderr),$remaining)) { return @{Code=-1;Text=''} }
        $text=$stdout.GetAwaiter().GetResult()
        if ($text.Length -gt 8192 -or $stderr.GetAwaiter().GetResult().Length -gt 8192) { return @{Code=-1;Text=''} }
        return @{Code=$process.ExitCode;Text=$text}
    } catch { return @{Code=-1;Text=''} }
    finally { $process.Dispose() }
}
function Get-SkyviewGitPreferences {
    $preferences=@(
        @{key='init.defaultBranch';recommended='main';status='unreadable';value=$null},
        @{key='fetch.prune';recommended='true';status='unreadable';value=$null},
        @{key='pull.ff';recommended='only';status='unreadable';value=$null}
    )
    $record=@{schema=1;component='Git';status='incomplete';reason='checkUnavailable';version=$null;scope='globalOutsideRepository';preferences=$preferences}
    $directory=$null
    try {
        $command=Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $command) { $record.status='notFound';$record.reason='notDiscovered';return $record }
        $directory=Join-Path ([IO.Path]::GetTempPath()) ('sde-git-check-'+[guid]::NewGuid().ToString('N'))
        $null=[IO.Directory]::CreateDirectory($directory)
        if (-not (Test-SkyviewGitSources $directory)) { $record.reason='configReadFailed';return $record }
        $prefix=@('--no-pager','--no-optional-locks')
        $probe=Invoke-SkyviewGitQuery $command.Source @('--version') $directory
        if ($probe.Code -ne 0 -or $probe.Text -notmatch '\Agit version (\d+\.\d+(?:\.\d+)?[A-Za-z0-9.+_-]{0,80})\s*\z') {
            $record.status=if ($probe.Code -eq -1) { 'incomplete' } else { 'unusable' }
            $record.reason='commandFailed'
            if ($probe.Code -gt 0) {
                $configProbe=Invoke-SkyviewGitQuery $command.Source ($prefix+@('config','--includes','--get','init.defaultBranch')) $directory
                if ($configProbe.Code -notin @(0,1)) { $record.status='incomplete';$record.reason='configReadFailed' }
            }
            return $record
        }
        $record.version=$Matches[1]
        # Parse applicable sources without dumping identity or credential data.
        $probe=Invoke-SkyviewGitQuery $command.Source ($prefix+@('config','--includes','--get','init.defaultBranch')) $directory
        $readable=$probe.Code -in @(0,1)
        $probe=Invoke-SkyviewGitQuery $command.Source ($prefix+@('config','--global','--includes','--show-origin','--null','--path','--get-all','include.path')) $directory
        $readable=(Test-SkyviewGitIncludes $probe $directory) -and $readable
        foreach ($preference in $preferences) {
            $arguments=$prefix+@('config','--global','--includes','--null')
            if ($preference.key -eq 'fetch.prune') { $arguments+=@('--type=bool') }
            $probe=Invoke-SkyviewGitQuery $command.Source ($arguments+@('--get',$preference.key)) $directory
            if ($probe.Code -eq 1 -and $probe.Text -eq '') { $preference.status='unset' }
            elseif ($probe.Code -eq 0 -and $probe.Text.EndsWith([string][char]0)) {
                $value=$probe.Text.Substring(0,$probe.Text.Length-1)
                if ($value.Length -le 512 -and $value -notmatch '[\x00-\x1f\x7f|]') {
                    $preference.value=$value
                    $preference.status=if ($value -ceq $preference.recommended) { 'matches' } else { 'different' }
                }
            }
            if ($preference.status -eq 'unreadable') { $readable=$false }
        }
        $record.status=if ($readable) { 'passed' } else { 'incomplete' }
        $record.reason=if ($readable) { 'verified' } else { 'configReadFailed' }
    } catch { $record.status='incomplete';$record.reason='checkUnavailable' }
    finally {
        if ($directory -and [IO.Directory]::Exists($directory)) {
            try { [IO.Directory]::Delete($directory) }
            catch { $record.status='incomplete';$record.reason='checkUnavailable' }
        }
    }
    return $record
}
