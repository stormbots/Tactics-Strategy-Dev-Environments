# Read-only bundle discovery. Loading this file performs no setup or IDE launch.
. (Join-Path $PSScriptRoot 'EditorLocation.ps1')
function New-SkyviewPyCharmLocation([string]$Status='incomplete',[string]$Reason='discoveryIncomplete') {
    [pscustomobject][ordered]@{schema=1;component='PyCharm';platform='windows';status=$Status;reason=$Reason;
        root=$null;launcher=$null;runtime=$null;version=$null;runtimeVersion=$null;productCode=$null;selectionId=$null;maintenanceEligibility='notEvaluated'}
}
function Get-SkyviewPyCharmCandidates {
    $roots=New-Object 'System.Collections.Generic.List[string]'
    $required=New-Object 'System.Collections.Generic.List[string]'
    $complete=$true
    $command=Get-Command pycharm64.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command -and (Split-Path (Split-Path $command.Source -Parent) -Leaf) -ieq 'bin') {
        $root=Split-Path (Split-Path $command.Source -Parent) -Parent
        $roots.Add($root);$required.Add($root)
    }
    foreach ($hive in @('HKCU:','HKLM:')) {
        foreach ($branch in @('SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall')) {
            try {
                $key=Join-Path $hive $branch
                if (-not (Test-Path -LiteralPath $key -ErrorAction Stop)) { continue }
                $keys=@(Get-ChildItem -LiteralPath $key -ErrorAction Stop)
                if ($keys.Count -gt 512) { $complete=$false }
                foreach ($entry in @($keys | Select-Object -First 512)) {
                    $value=Get-ItemProperty -LiteralPath $entry.PSPath -ErrorAction Stop
                    if ($value.DisplayName -match '\APyCharm(?: Community Edition)?(?: \d.*)?\z') {
                        if ($value.InstallLocation) { $roots.Add([string]$value.InstallLocation);$required.Add([string]$value.InstallLocation) }
                        else { $complete=$false }
                    }
                }
            } catch { $complete=$false }
        }
    }
    $parents=@()
    foreach ($parent in @($env:ProgramFiles,${env:ProgramFiles(x86)})) { if ($parent) { $parents+=Join-Path $parent 'JetBrains' } }
    if ($env:LOCALAPPDATA) {
        $parents+=Join-Path $env:LOCALAPPDATA 'Programs'
        $parents+=Join-Path $env:LOCALAPPDATA 'JetBrains\Toolbox\apps'
    }
    foreach ($parent in $parents) {
        try {
            if (-not (Test-Path -LiteralPath $parent -ErrorAction Stop)) { continue }
            $children=@(Get-ChildItem -LiteralPath $parent -Directory -ErrorAction Stop)
            if ($children.Count -gt 256) { $complete=$false }
            foreach ($child in @($children | Select-Object -First 256 | Where-Object Name -Match '\Apycharm(?:[-_ ].*)?\z' | Sort-Object FullName)) { $roots.Add($child.FullName) }
        } catch { $complete=$false }
    }
    $unique=@($roots | Select-Object -Unique)
    if ($unique.Count -gt 12) { $complete=$false }
    [pscustomobject]@{Roots=@($unique | Select-Object -First 12);RequiredRoots=@($required);Complete=$complete}
}
function Test-SkyviewPyCharmNativeFile([string]$Path,[long]$Maximum) {
    $null=Get-SkyviewEditorFile $Path $Maximum
    $stream=[IO.File]::OpenRead($Path)
    try {
        $reader=New-Object IO.BinaryReader($stream)
        if ($stream.Length -lt 64 -or $reader.ReadUInt16() -ne 0x5a4d) { throw 'unsupportedLayout' }
        $stream.Position=60;$offset=$reader.ReadUInt32()
        if ($offset -lt 64 -or $offset -gt 4096 -or $offset+6 -gt $stream.Length) { throw 'unsupportedLayout' }
        $stream.Position=$offset
        if ($reader.ReadUInt32() -ne 0x00004550 -or $reader.ReadUInt16() -ne 0x8664) { throw 'unsupportedLayout' }
    } finally { $stream.Dispose() }
}
function Get-SkyviewPyCharmLayout([string]$Root) {
    if (-not $Root -or $Root -notmatch '\A[A-Za-z]:\\') { throw 'unsupportedLayout' }
    $rootPath=[IO.Path]::GetFullPath($Root).TrimEnd('\')
    $info=Read-SkyviewEditorJson (Join-Path $rootPath 'product-info.json')
    if ($info.name -cnotin @('PyCharm','PyCharm Community Edition') -or $info.productCode -cnotin @('PC','PY') -or
        $info.version -isnot [string] -or $info.version -notmatch '\A20\d{2}\.\d{1,2}(?:\.\d{1,3}){0,2}\z') { throw 'wrongProduct' }
    if ($info.launch -isnot [array] -or $info.launch.Count -gt 8) { throw 'unsupportedLayout' }
    if ($null -ne $info.minRequiredJavaVersion -and
        (($info.minRequiredJavaVersion -isnot [int] -and $info.minRequiredJavaVersion -isnot [long]) -or
         $info.minRequiredJavaVersion -lt 1 -or $info.minRequiredJavaVersion -gt 999)) { throw 'unsupportedLayout' }
    $launch=@($info.launch | Where-Object { $_.os -ceq 'Windows' -and (-not $_.arch -or $_.arch -ceq 'amd64') })
    if ($launch.Count -ne 1 -or $launch[0].launcherPath -cne 'bin/pycharm64.exe' -or $launch[0].javaExecutablePath -cne 'jbr/bin/java.exe') { throw 'unsupportedLayout' }
    $launcher=Join-Path $rootPath 'bin\pycharm64.exe';$runtime=Join-Path $rootPath 'jbr\bin\java.exe'
    Test-SkyviewPyCharmNativeFile $launcher 16777216
    Test-SkyviewPyCharmNativeFile $runtime 536870912
    [pscustomobject]@{Root=$rootPath;Launcher=$launcher;Runtime=$runtime;Info=$info}
}
function Get-SkyviewPyCharmFingerprint($Layout) {
    $paths=@(@{Path=(Join-Path $Layout.Root 'product-info.json');Limit=1048576},
        @{Path=$Layout.Launcher;Limit=16777216},@{Path=$Layout.Runtime;Limit=536870912})
    $hashes=@(foreach ($file in $paths) {
        $null=Get-SkyviewEditorFile $file.Path $file.Limit
        (Get-FileHash -LiteralPath $file.Path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
    })
    $sha=[Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($hashes -join "`n")+"`n"+$Layout.Root)))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Get-SkyviewPyCharmLocation {
    if (-not (Test-SkyviewEditorOrdinaryUser)) { return New-SkyviewPyCharmLocation incomplete normalUserRequired }
    $record=New-SkyviewPyCharmLocation
    $clock=[Diagnostics.Stopwatch]::StartNew()
    try {
        $candidates=Get-SkyviewPyCharmCandidates
        $incomplete=-not $candidates.Complete -or $candidates.Roots.Count -gt 12;$unusable=$false
        foreach ($rootPath in @($candidates.Roots | Select-Object -First 12)) {
            if ($clock.ElapsedMilliseconds -ge 15000) { $incomplete=$true;break }
            try {
                if (-not (Test-Path -LiteralPath $rootPath -ErrorAction Stop)) {
                    if ($candidates.RequiredRoots -contains $rootPath) { $incomplete=$true;$record.reason='staleRegistration' };continue
                }
                $layout=Get-SkyviewPyCharmLayout $rootPath
                $before=Get-SkyviewPyCharmFingerprint $layout
                $probe=Invoke-SkyviewEditorQuery $layout.Runtime @('--version') ([Math]::Min(4000,15000-[int]$clock.ElapsedMilliseconds))
                if ($probe.Code -ne 0 -or $probe.Text -notmatch '(?m)^(?:openjdk|java) (\d+(?:\.[0-9]+)*(?:[+_.-][\w.+-]+)?)(?:\s|$)' -or $probe.Text -cnotmatch 'JBR-') {
                    if ($probe.Code -eq -1) { $incomplete=$true;$record.reason='runtimeCheckIncomplete' }
                    else { $unusable=$true;$record.reason='runtimeCheckFailed' };continue
                }
                $runtimeVersion=[regex]::Match($probe.Text,'(?m)^(?:openjdk|java) (\d+(?:\.[0-9]+)*(?:[+_.-][\w.+-]+)?)(?:\s|$)').Groups[1].Value
                if ($runtimeVersion.Length -gt 80 -or ($null -ne $layout.Info.minRequiredJavaVersion -and [int]([regex]::Match($runtimeVersion,'\A\d+').Value) -lt $layout.Info.minRequiredJavaVersion)) {
                    $unusable=$true;$record.reason='runtimeCheckFailed';continue
                }
                if ($before -cne (Get-SkyviewPyCharmFingerprint $layout)) { $incomplete=$true;$record.reason='changedDuringCheck';continue }
                $record.status='verified';$record.reason='verified';$record.root=$layout.Root
                $record.launcher=$layout.Launcher;$record.runtime=$layout.Runtime;$record.version=$layout.Info.version
                $record.productCode=$layout.Info.productCode;$record.runtimeVersion=$runtimeVersion;$record.selectionId=$before
                return $record
            } catch {
                if ($_.Exception.ToString() -match 'UnauthorizedAccess|PermissionDenied') { $incomplete=$true;$record.reason='accessDenied' }
                elseif ($_.Exception.Message -eq 'wrongProduct') { $unusable=$true;$record.reason='wrongProduct' }
                else { $incomplete=$true }
            }
        }
        if ($incomplete) { return $record }
        if ($unusable) { return New-SkyviewPyCharmLocation unusable $record.reason }
        return New-SkyviewPyCharmLocation notFound notDiscovered
    } catch { return $record }
}
