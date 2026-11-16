# Read-only stable VSCodium selection. No package, preference or elevation authority.
function Test-SkyviewEditorOrdinaryUser {
    try {
        $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
        $principal=New-Object Security.Principal.WindowsPrincipal($identity)
        return -not $identity.IsSystem -and -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch { return $false }
}
function New-SkyviewEditorLocation([string]$Status='incomplete',[string]$Reason='discoveryIncomplete') {
    [pscustomobject][ordered]@{schema=1;component='VSCodium';platform='windows';status=$Status;reason=$Reason;
        root=$null;executable=$null;cli=$null;version=$null;electronVersion=$null;selectionId=$null;maintenanceEligibility='notEvaluated'}
}
function Get-SkyviewEditorFile([string]$Path,[long]$Maximum) {
    if (-not $Path -or $Path.Length -gt 4096 -or $Path -notmatch '\A[A-Za-z]:\\' -or $Path -match '[\x00-\x1f\x7f|]') { throw 'unsupportedLayout' }
    $full=[IO.Path]::GetFullPath($Path)
    if (-not [string]::Equals($full,$Path,[StringComparison]::OrdinalIgnoreCase)) { throw 'unsupportedLayout' }
    $item=Get-Item -LiteralPath $full -Force -ErrorAction Stop
    if ($item.PSIsContainer -or $item.Length -gt $Maximum) { throw 'inspectionLimit' }
    # Reject links/junctions rather than inspecting one target then opening another.
    $part=$item
    while ($part) {
        if ($part.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'unsupportedLayout' }
        $part=if ($part -is [IO.FileInfo]) { $part.Directory } else { $part.Parent }
    }
    return $item
}
function Read-SkyviewEditorJson([string]$Path) {
    $null=Get-SkyviewEditorFile $Path 1048576
    $file=[IO.File]::OpenRead($Path)
    try {
        $bytes=New-Object byte[] 1048577
        $total=0
        while ($total -lt $bytes.Length) {
            $count=$file.Read($bytes,$total,$bytes.Length-$total)
            if ($count -eq 0) { break }; $total+=$count
        }
        if ($total -gt 1048576) { throw 'inspectionLimit' }
        $utf8=New-Object Text.UTF8Encoding($false,$true)
        return $utf8.GetString($bytes,0,$total) | ConvertFrom-Json -ErrorAction Stop
    } finally { $file.Dispose() }
}
function Test-SkyviewEditorLayout([string]$Executable) {
    $null=Get-SkyviewEditorFile $Executable 536870912
    if ([IO.Path]::GetFileName($Executable) -ine 'VSCodium.exe') { throw 'unsupportedLayout' }
    $file=[IO.File]::OpenRead($Executable)
    try {
        $reader=New-Object IO.BinaryReader($file)
        if ($file.Length -lt 64 -or $reader.ReadUInt16() -ne 0x5a4d) { throw 'unsupportedLayout' }
        $file.Position=60; $offset=$reader.ReadUInt32()
        if ($offset -lt 64 -or $offset -gt 4096 -or $offset+4 -gt $file.Length) { throw 'unsupportedLayout' }
        $file.Position=$offset
        if ($reader.ReadUInt32() -ne 0x00004550) { throw 'unsupportedLayout' }
    } finally { $file.Dispose() }
    $root=Split-Path -Parent $Executable
    $product=Read-SkyviewEditorJson (Join-Path $root 'resources\app\product.json')
    $package=Read-SkyviewEditorJson (Join-Path $root 'resources\app\package.json')
    $null=Get-SkyviewEditorFile (Join-Path $root 'resources\app\out\cli.js') 16777216
    if ($product.nameShort -cne 'VSCodium' -or $product.applicationName -cne 'codium' -or $product.quality -cne 'stable' -or
        $package.version -isnot [string] -or $package.version.Length -gt 80 -or $package.version -notmatch '\A\d+\.\d+\.\d+(?:\.\d+)?\z') { throw 'wrongProduct' }
    return [string]$package.version
}
function Get-SkyviewEditorFingerprint([string]$Executable) {
    $root=Split-Path -Parent $Executable
    $files=@(@{Path=$Executable;Limit=536870912},
        @{Path=(Join-Path $root 'resources\app\product.json');Limit=1048576},
        @{Path=(Join-Path $root 'resources\app\package.json');Limit=1048576},
        @{Path=(Join-Path $root 'resources\app\out\cli.js');Limit=16777216})
    $hashes=@(foreach ($entry in $files) {
        $null=Get-SkyviewEditorFile $entry.Path $entry.Limit
        $stream=[IO.File]::OpenRead($entry.Path)
        $algorithm=[Security.Cryptography.SHA256]::Create()
        try { ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
        finally { $algorithm.Dispose(); $stream.Dispose() }
    })
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($hashes -join "`n")+"`n"+$Executable)))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Invoke-SkyviewEditorQuery([string]$Executable,[string[]]$Arguments,[int]$TimeoutMs) {
    if ($TimeoutMs -le 0) { return @{Code=-1;Text=''} }
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$Executable
    $start.Arguments=(@($Arguments | ForEach-Object { '"'+(($_ -replace '(\\*)"','$1$1\"') -replace '(\\+)$','$1$1')+'"' }) -join ' ')
    $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.WorkingDirectory=[IO.Path]::GetTempPath()
    foreach ($key in @('NODE_OPTIONS','NODE_PATH','NODE_COMPILE_CACHE','NODE_V8_COVERAGE','VSCODE_DEV','VSCODE_CWD','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')) { $start.EnvironmentVariables.Remove($key) }
    $start.EnvironmentVariables['ELECTRON_RUN_AS_NODE']='1'
    $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    $process=New-Object Diagnostics.Process
    $process.StartInfo=$start
    $clock=[Diagnostics.Stopwatch]::StartNew()
    $started=$false
    try {
        $started=$process.Start()
        $sides=@(@{Stream=$process.StandardOutput.BaseStream},@{Stream=$process.StandardError.BaseStream})
        foreach ($side in $sides) {
            $side.Buffer=New-Object byte[] 4096
            $side.Bytes=New-Object 'System.Collections.Generic.List[byte]'
            $side.Pending=$side.Stream.ReadAsync($side.Buffer,0,4096)
        }
        while (@($sides | Where-Object { $null -ne $_.Pending }).Count -or -not $process.HasExited) {
            foreach ($side in $sides) {
                if ($side.Pending -and $side.Pending.IsCompleted) {
                    $count=$side.Pending.GetAwaiter().GetResult()
                    if ($count -eq 0) { $side.Pending=$null }
                    else {
                        $side.Bytes.AddRange([byte[]]$side.Buffer[0..($count-1)])
                        if ($side.Bytes.Count -gt 32768) { return @{Code=-1;Text=''} }
                        $side.Pending=$side.Stream.ReadAsync($side.Buffer,0,4096)
                    }
                }
            }
            if ($clock.ElapsedMilliseconds -ge $TimeoutMs) { return @{Code=-1;Text=''} }
            Start-Sleep -Milliseconds 10
        }
        $utf8=New-Object Text.UTF8Encoding($false,$true)
        return @{Code=$process.ExitCode;Text=$utf8.GetString($sides[0].Bytes.ToArray()).Trim()}
    } catch { return @{Code=-1;Text=''} }
    finally {
        # Only our own fixed diagnostic child; never a package/installer worker.
        try { if ($started -and -not $process.HasExited) { $process.Kill() } } catch { }
        $process.Dispose()
    }
}
function Get-SkyviewEditorCandidates {
    $paths=New-Object 'System.Collections.Generic.List[string]'
    $required=New-Object 'System.Collections.Generic.List[string]'
    $complete=$true
    foreach ($name in @('codium.cmd','VSCodium.exe')) {
        $entry=Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($entry) {
            $path=$entry.Source
            if ([IO.Path]::GetFileName($path) -ieq 'codium.cmd' -and (Split-Path (Split-Path $path -Parent) -Leaf) -ieq 'bin') { $path=Join-Path (Split-Path (Split-Path $path -Parent) -Parent) 'VSCodium.exe' }
            $paths.Add($path); $required.Add($path)
        }
    }
    foreach ($hive in @('HKCU:','HKLM:')) {
        foreach ($branch in @('SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\VSCodium.exe','SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\VSCodium.exe')) {
            try {
                $key=Join-Path $hive $branch
                if (Test-Path -LiteralPath $key -ErrorAction Stop) {
                    $path=[string](Get-Item -LiteralPath $key -ErrorAction Stop).GetValue('')
                    if ($path) { $paths.Add($path); $required.Add($path) } else { $complete=$false }
                }
            } catch { $complete=$false }
        }
        foreach ($branch in @('SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall')) {
            try {
                $key=Join-Path $hive $branch
                if (-not (Test-Path -LiteralPath $key -ErrorAction Stop)) { continue }
                $keys=@(Get-ChildItem -LiteralPath $key -ErrorAction Stop)
                if ($keys.Count -gt 512) { $complete=$false }
                foreach ($entry in @($keys | Select-Object -First 512)) {
                    $value=Get-ItemProperty -LiteralPath $entry.PSPath -ErrorAction Stop
                    if ($value.DisplayName -in @('VSCodium','VSCodium (User)')) {
                        if ($value.InstallLocation) {
                            $path=Join-Path $value.InstallLocation 'VSCodium.exe'
                            $paths.Add($path); $required.Add($path)
                        } else { $complete=$false }
                    }
                }
            } catch { $complete=$false }
        }
    }
    foreach ($parent in @($env:ProgramFiles,${env:ProgramFiles(x86)})) { if ($parent) { $paths.Add((Join-Path $parent 'VSCodium\VSCodium.exe')) } }
    if ($env:LOCALAPPDATA) { $paths.Add((Join-Path $env:LOCALAPPDATA 'Programs\VSCodium\VSCodium.exe')) }
    $unique=@($paths | Select-Object -Unique)
    if ($unique.Count -gt 12) { $complete=$false }
    [pscustomobject]@{Paths=@($unique | Select-Object -First 12);RequiredPaths=@($required);Complete=$complete}
}
function ConvertFrom-SkyviewEditorLocation([string]$Text,[string]$Executable,[string]$Version) {
    try {
        if ($Text.Length -gt 32768) { return $null }
        $value=$Text | ConvertFrom-Json -ErrorAction Stop
        if (((@($value.PSObject.Properties.Name) | Sort-Object) -join ',') -cne 'cli,component,electronVersion,executable,maintenanceEligibility,platform,reason,root,schema,selectionId,status,version' -or
            ($value.schema -isnot [int] -and $value.schema -isnot [long]) -or $value.schema -ne 1 -or $value.component -cne 'VSCodium' -or
            $value.platform -cne 'windows' -or $value.status -cne 'candidate' -or $value.reason -cne 'identityObserved' -or $value.maintenanceEligibility -cne 'notEvaluated' -or
            $value.version -cne $Version -or $value.electronVersion -isnot [string] -or $value.electronVersion.Length -gt 80 -or $value.electronVersion -notmatch '\A\d+\.\d+\.\d+(?:[-+][\w.-]+)?\z' -or
            $value.selectionId -isnot [string] -or $value.selectionId -cnotmatch '\A[a-f0-9]{64}\z' -or
            -not [string]::Equals($value.executable,$Executable,[StringComparison]::OrdinalIgnoreCase) -or
            -not [string]::Equals($value.root,(Split-Path $Executable -Parent),[StringComparison]::OrdinalIgnoreCase) -or
            -not [string]::Equals($value.cli,(Join-Path $value.root 'resources\app\out\cli.js'),[StringComparison]::OrdinalIgnoreCase)) { return $null }
        $null=Get-SkyviewEditorFile $value.executable 536870912
        if ((Get-SkyviewEditorFingerprint $value.executable) -cne $value.selectionId) { return $null }
        return $value
    } catch { return $null }
}
function Get-SkyviewEditorLocation {
    if (-not (Test-SkyviewEditorOrdinaryUser)) { return New-SkyviewEditorLocation incomplete normalUserRequired }
    $clock=[Diagnostics.Stopwatch]::StartNew()
    $record=New-SkyviewEditorLocation
    try {
        $candidates=Get-SkyviewEditorCandidates
        $incomplete=-not $candidates.Complete -or $candidates.Paths.Count -gt 12
        $unusable=$false
        foreach ($path in @($candidates.Paths | Select-Object -First 12)) {
            if ($clock.ElapsedMilliseconds -ge 15000) { $incomplete=$true; break }
            try {
                if (-not (Test-Path -LiteralPath $path -ErrorAction Stop)) {
                    if ($candidates.RequiredPaths -contains $path) { $incomplete=$true; $record.reason='staleRegistration' }; continue
                }
                $version=Test-SkyviewEditorLayout $path
                $identity=Invoke-SkyviewEditorQuery $path @((Join-Path $PSScriptRoot 'EditorIdentityProbe.cjs')) ([Math]::Min(6000,15000-[int]$clock.ElapsedMilliseconds))
                $value=if ($identity.Code -eq 0) { ConvertFrom-SkyviewEditorLocation $identity.Text $path $version } else { $null }
                if (-not $value) { $incomplete=$true; continue }
                $actual=Invoke-SkyviewEditorQuery $value.executable @($value.cli,'--version') ([Math]::Min(3000,15000-[int]$clock.ElapsedMilliseconds))
                if ($actual.Code -ne 0 -or ($actual.Text -split '\r?\n')[0] -cne $version) {
                    if ($actual.Code -eq -1) { $incomplete=$true } else { $unusable=$true }; continue
                }
                if ((Get-SkyviewEditorFingerprint $value.executable) -cne $value.selectionId) { $incomplete=$true; $record.reason='changedDuringCheck'; continue }
                $value.status='verified'; $value.reason='verified'
                return $value
            } catch {
                if ($_.Exception.ToString() -match 'UnauthorizedAccess|PermissionDenied') { $incomplete=$true; $record.reason='accessDenied' }
                elseif ($_.Exception.Message -in @('wrongProduct','unsupportedLayout')) { $unusable=$true; $record.reason=$_.Exception.Message }
                else { $incomplete=$true }
            }
        }
        if ($incomplete) { return $record }
        if ($unusable) { return New-SkyviewEditorLocation unusable $record.reason }
        return New-SkyviewEditorLocation notFound notDiscovered
    } catch { return $record }
}
function Get-SkyviewEditorRequiredChecks($Observation) {
    # Structured results for the validator; no partial extension passes on failure.
    if ($Observation.status -cne 'verified') {
        $message=if ($Observation.status -ceq 'notFound') { 'The supported search did not find VSCodium.' }
            elseif ($Observation.reason -ceq 'normalUserRequired') { 'Open SDE without administrator privileges to check VSCodium.' }
            else { 'SDE could not finish checking this VSCodium installation. Review the check details.' }
        return [pscustomobject]@{Status='FAIL';Message=('VSCodium: '+$message)}
    }
    [pscustomobject]@{Status='PASS';Message="VSCodium: $($Observation.version); application identity and selected launcher verified"}
    try {
        $policy=Join-Path $PSScriptRoot 'extensions.txt'
        $null=Get-SkyviewEditorFile $policy 65536
        $required=@(Get-Content -LiteralPath $policy -ErrorAction Stop | Where-Object { $_.Trim() -and $_ -notmatch '^\s*#' } | ForEach-Object { $_.Trim() })
        if (-not $required.Count -or @($required | Where-Object { $_ -notmatch '\A[A-Za-z0-9_-]+\.[A-Za-z0-9_.-]+\z' }).Count) { throw 'extensionPolicy' }
        $output=Invoke-SkyviewEditorQuery $Observation.executable @($Observation.cli,'--list-extensions') 6000
        if ($output.Code -ne 0 -or (Get-SkyviewEditorFingerprint $Observation.executable) -cne $Observation.selectionId) { throw 'extensionCheck' }
        $installed=@($output.Text -split '\r?\n')
        foreach ($extension in $required) {
            [pscustomobject]@{Status=$(if ($installed -contains $extension) { 'PASS' } else { 'FAIL' });Message="VSCodium extension: $extension"}
        }
    } catch { [pscustomobject]@{Status='FAIL';Message='VSCodium: SDE could not finish checking the installed extensions.'} }
}
