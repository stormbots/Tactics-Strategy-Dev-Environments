# Bounded ordinary-user observations. No IDE/browser launch or update authority.
. (Join-Path $PSScriptRoot 'EditorLocation.ps1')
function New-SkyviewApplicationLocation([string]$Tool,[string]$Status='incomplete',[string]$Reason='discoveryIncomplete') {
    [pscustomobject][ordered]@{schema=1;component=$Tool;platform='windows';status=$Status;reason=$Reason;root=$null;
        executable=$null;version=$null;runtimeVersion=$null;selectionId=$null;verificationScope=$null;maintenanceEligibility='notEvaluated'}
}
function Read-SkyviewApplicationText([string]$Path,[int]$Maximum=65536) {
    $null=Get-SkyviewEditorFile $Path $Maximum
    $stream=[IO.File]::OpenRead($Path)
    try {
        $bytes=New-Object byte[] ($Maximum+1);$total=0
        while ($total -lt $bytes.Length) {
            $count=$stream.Read($bytes,$total,$bytes.Length-$total)
            if ($count -eq 0) { break };$total+=$count
        }
        if ($total -gt $Maximum) { throw 'inspectionLimit' }
        $utf8=New-Object Text.UTF8Encoding($false,$true)
        return $utf8.GetString($bytes,0,$total).TrimStart([char]0xfeff)
    } finally { $stream.Dispose() }
}
function ConvertFrom-SkyviewApplicationProperties([string]$Text,[string]$Section='') {
    $values=@{};$active=-not $Section;$sections=0
    foreach ($line in ($Text -split '\r?\n')) {
        if ($Section -and $line -match '\A\[([^\]]+)\]\s*\z') {
            $active=$Matches[1] -ceq $Section
            if ($active) { $sections++;if ($sections -gt 1) { throw 'metadataIncomplete' } };continue
        }
        if (-not $active -or -not $line.Trim() -or $line -match '^\s*[#!;]') { continue }
        $index=$line.IndexOf('=')
        if ($index -lt 1) { throw 'metadataIncomplete' }
        $key=$line.Substring(0,$index).Trim()
        if ($values.ContainsKey($key)) { throw 'metadataIncomplete' }
        $values[$key]=$line.Substring($index+1).Trim()
    }
    return $values
}
function Get-SkyviewApplicationCandidates([string]$Tool) {
    $names=@{DBeaver=@('dbeaver.exe','dbeaver-ce.exe');Chrome=@('chrome.exe');Firefox=@('firefox.exe')}[$Tool]
    $display=@{DBeaver='\ADBeaver(?: Community(?: Edition)?)?(?: \d.*)?\z';Chrome='\AGoogle Chrome(?: .*)?\z';Firefox='\A(?:Mozilla )?Firefox(?: .*)?\z'}[$Tool]
    $paths=New-Object 'System.Collections.Generic.List[string]';$required=New-Object 'System.Collections.Generic.List[string]'
    $complete=$true
    foreach ($name in $names) {
        $command=Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) { $paths.Add($command.Source);$required.Add($command.Source) }
    }
    foreach ($hive in @('HKCU:','HKLM:')) {
        foreach ($prefix in @('SOFTWARE','SOFTWARE\WOW6432Node')) {
            foreach ($name in $names) {
                try {
                    $key=Join-Path $hive "$prefix\Microsoft\Windows\CurrentVersion\App Paths\$name"
                    if (Test-Path -LiteralPath $key -ErrorAction Stop) {
                        $value=[string](Get-Item -LiteralPath $key -ErrorAction Stop).GetValue('')
                        if ($value) { $paths.Add($value);$required.Add($value) } else { $complete=$false }
                    }
                } catch { $complete=$false }
            }
            try {
                $key=Join-Path $hive "$prefix\Microsoft\Windows\CurrentVersion\Uninstall"
                if (-not (Test-Path -LiteralPath $key -ErrorAction Stop)) { continue }
                $keys=@(Get-ChildItem -LiteralPath $key -ErrorAction Stop)
                if ($keys.Count -gt 512) { $complete=$false }
                foreach ($entry in @($keys | Select-Object -First 512)) {
                    $value=Get-ItemProperty -LiteralPath $entry.PSPath -ErrorAction Stop
                    if ($value.DisplayName -match $display) {
                        if ($value.InstallLocation) {
                            foreach ($name in $names) {
                                $target=Join-Path $value.InstallLocation $name
                                $paths.Add($target);$required.Add($target)
                                if ($Tool -eq 'Chrome') { $paths.Add((Join-Path $value.InstallLocation "Application\$name")) }
                            }
                        } else { $complete=$false }
                    }
                }
            } catch { $complete=$false }
        }
    }
    foreach ($parent in @($env:ProgramFiles,${env:ProgramFiles(x86)},$env:LOCALAPPDATA)) {
        if (-not $parent) { continue }
        $relative=@{DBeaver=@('DBeaver\dbeaver.exe','DBeaver\dbeaver-ce.exe','Programs\DBeaver\dbeaver.exe');
            Chrome=@('Google\Chrome\Application\chrome.exe');Firefox=@('Mozilla Firefox\firefox.exe','Programs\Mozilla Firefox\firefox.exe')}[$Tool]
        foreach ($suffix in $relative) { $paths.Add((Join-Path $parent $suffix)) }
    }
    $unique=@($paths | Select-Object -Unique)
    if ($unique.Count -gt 12) { $complete=$false }
    [pscustomobject]@{Paths=@($unique | Select-Object -First 12);RequiredPaths=@($required);Complete=$complete}
}
function Test-SkyviewApplicationNativeFile([string]$Path,[long]$Maximum=536870912) {
    $null=Get-SkyviewEditorFile $Path $Maximum
    $stream=[IO.File]::OpenRead($Path)
    try {
        $reader=New-Object IO.BinaryReader($stream)
        if ($stream.Length -lt 64 -or $reader.ReadUInt16() -ne 0x5a4d) { throw 'unsupportedLayout' }
        $stream.Position=60;$offset=$reader.ReadUInt32()
        if ($offset -lt 64 -or $offset -gt 4096 -or $offset+6 -gt $stream.Length) { throw 'unsupportedLayout' }
        $stream.Position=$offset
        if ($reader.ReadUInt32() -ne 0x00004550) { throw 'unsupportedLayout' }
        $machine=$reader.ReadUInt16()
        if ($machine -notin @(0x8664,0x14c)) { throw 'unsupportedLayout' }
        return $machine
    } finally { $stream.Dispose() }
}
function Get-SkyviewDBeaverLayout([string]$Executable) {
    $root=Split-Path $Executable -Parent
    $productFile=Join-Path $root '.eclipseproduct'
    $product=ConvertFrom-SkyviewApplicationProperties (Read-SkyviewApplicationText $productFile)
    if ($product.name -cne 'DBeaver' -or $product.id -cne 'org.jkiss.dbeaver.product' -or
        $product.version -notmatch '\A\d+\.\d+\.\d+(?:\.\d+)?\z' -or $product.version.Length -gt 80) { throw 'wrongProduct' }
    $iniFile=Join-Path $root 'dbeaver.ini'
    $lines=@((Read-SkyviewApplicationText $iniFile) -split '\r?\n' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $startup=@();$vms=@();$minimum=@()
    for ($index=0;$index -lt $lines.Count;$index++) {
        if ($lines[$index] -in @('-startup','-vm')) {
            if ($index+1 -ge $lines.Count) { throw 'unsupportedLayout' }
            if ($lines[$index] -eq '-startup') { $startup+=($lines[$index+1] -replace '\\','/') }
            else { $vms+=($lines[$index+1] -replace '\\','/') }
        }
        if ($lines[$index] -match '\A-Dosgi\.requiredJavaVersion=(\d{1,3})\z') { $minimum+=[int]$Matches[1] }
    }
    if ($startup.Count -ne 1 -or $startup[0] -notmatch '\Aplugins/org\.(?:jkiss\.dbeaver|eclipse\.equinox)\.launcher_[A-Za-z0-9_.-]+\.jar\z' -or $minimum.Count -gt 1 -or $vms.Count -gt 1) { throw 'unsupportedLayout' }
    $jar=Join-Path $root ($startup[0] -replace '/','\')
    $null=Get-SkyviewEditorFile $jar 67108864
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive=[IO.Compression.ZipFile]::OpenRead($jar)
    try {
        $entry=$archive.GetEntry('META-INF/MANIFEST.MF')
        if (-not $entry -or $entry.Length -gt 65536) { throw 'metadataIncomplete' }
        $stream=$entry.Open()
        try {
            $bytes=New-Object byte[] 65537;$total=0
            while ($total -lt $bytes.Length) { $n=$stream.Read($bytes,$total,$bytes.Length-$total);if ($n -eq 0) { break };$total+=$n }
            if ($total -gt 65536) { throw 'inspectionLimit' }
            $utf8=New-Object Text.UTF8Encoding($false,$true)
            $manifest=$utf8.GetString($bytes,0,$total) -replace '\r?\n ',''
            if ($manifest -cnotmatch '(?m)^Bundle-SymbolicName: (org\.(?:jkiss\.dbeaver|eclipse\.equinox)\.launcher)(?:;|\r?$)') { throw 'wrongProduct' }
        } finally { $stream.Dispose() }
    } finally { $archive.Dispose() }
    $vm=if ($vms.Count) { $vms[0] } else { 'jre/bin/javaw.exe' }
    if ($vm -match '\A[A-Za-z]:/') {
        $prefix=($root -replace '\\','/').TrimEnd('/')+'/'
        if (-not $vm.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'unsupportedLayout' }
        $vm=$vm.Substring($prefix.Length)
    }
    if ($vm.EndsWith('/bin')) { $vm+='/javaw.exe' }
    if ($vm -notmatch '\A(?:[^/:\x00-\x1f|]+/)+bin/javaw?\.exe\z' -or @($vm.Split('/') | Where-Object { $_ -in @('.','..') }).Count) { throw 'unsupportedLayout' }
    $target=Join-Path $root ($vm -replace '/','\')
    $runtime=Join-Path (Split-Path $target -Parent) 'java.exe'
    $machine=Test-SkyviewApplicationNativeFile $Executable 67108864
    if ((Test-SkyviewApplicationNativeFile $target) -ne $machine -or (Test-SkyviewApplicationNativeFile $runtime) -ne $machine) { throw 'unsupportedLayout' }
    [pscustomobject]@{Version=$product.version;Runtime=$runtime;Minimum=$(if ($minimum.Count) { $minimum[0] } else { 1 });Files=@($productFile,$iniFile,$jar,$target,$runtime)}
}
function Get-SkyviewApplicationFingerprint([string[]]$Files,[string]$Root) {
    $hashes=@(foreach ($file in $Files) {
        $null=Get-SkyviewEditorFile $file 536870912
        (Get-FileHash -LiteralPath $file -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
    })
    $sha=[Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($hashes -join "`n")+"`n"+$Root)))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Get-SkyviewApplicationLocation([ValidateSet('DBeaver','Chrome','Firefox')][string]$Tool) {
    if (-not (Test-SkyviewEditorOrdinaryUser)) { return New-SkyviewApplicationLocation $Tool incomplete normalUserRequired }
    $record=New-SkyviewApplicationLocation $Tool
    $clock=[Diagnostics.Stopwatch]::StartNew()
    try {
        $search=Get-SkyviewApplicationCandidates $Tool
        $incomplete=-not $search.Complete -or $search.Paths.Count -gt 12;$unusable=$false
        foreach ($path in @($search.Paths | Select-Object -First 12)) {
            try {
                if ($clock.ElapsedMilliseconds -ge 15000) { $incomplete=$true;break }
                if (-not (Test-Path -LiteralPath $path -ErrorAction Stop)) {
                    if ($search.RequiredPaths -contains $path) { $incomplete=$true;$record.reason='staleRegistration' };continue
                }
                $null=Test-SkyviewApplicationNativeFile $path
                $root=Split-Path $path -Parent;$files=@($path);$runtimeVersion=$null
                if ($Tool -eq 'DBeaver') {
                    if ([IO.Path]::GetFileName($path) -inotmatch '\Adbeaver(?:-ce)?\.exe\z') { throw 'wrongProduct' }
                    $layout=Get-SkyviewDBeaverLayout $path;$version=$layout.Version;$files+=@($layout.Files)
                } else {
                    $info=[Diagnostics.FileVersionInfo]::GetVersionInfo($path)
                    $expected=@{Chrome=@('Google Chrome');Firefox=@('Firefox','Mozilla Firefox')}[$Tool]
                    $pattern=if ($Tool -eq 'Firefox') { '\A(\d+(?:\.\d+){1,3})(?:esr)?\z' } else { '\A(\d+(?:\.\d+){1,3})\z' }
                    $match=[regex]::Match($info.ProductVersion,$pattern)
                    if ($info.ProductName -cnotin $expected -or -not $match.Success -or $info.ProductVersion.Length -gt 80) { throw 'wrongProduct' }
                    $version=$match.Groups[1].Value
                    if ($Tool -eq 'Firefox') {
                        $file=Join-Path $root 'application.ini';$files+=@($file)
                        $app=ConvertFrom-SkyviewApplicationProperties (Read-SkyviewApplicationText $file) App
                        if ($app.Name -cne 'Firefox' -or $app.ID -ine '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}' -or ($app.Version -creplace 'esr$','') -cne $version) { throw 'wrongProduct' }
                    }
                }
                $before=Get-SkyviewApplicationFingerprint $files $root
                if ($Tool -eq 'DBeaver') {
                    $probe=Invoke-SkyviewEditorQuery $layout.Runtime @('--version') ([Math]::Min(4000,15000-[int]$clock.ElapsedMilliseconds))
                    $match=[regex]::Match($probe.Text,'(?m)^(?:openjdk|java) (\d+(?:\.\d+)*(?:[+_.-][\w.+-]+)?)(?:\s|$)')
                    if ($probe.Code -ne 0 -or -not $match.Success -or $match.Groups[1].Value.Length -gt 80 -or [int]([regex]::Match($match.Groups[1].Value,'\A\d+').Value) -lt $layout.Minimum) {
                        if ($probe.Code -eq -1) { $incomplete=$true } else { $unusable=$true };$record.reason='runtimeCheckFailed';continue
                    }
                    $runtimeVersion=$match.Groups[1].Value
                }
                if ($before -cne (Get-SkyviewApplicationFingerprint $files $root)) { $incomplete=$true;$record.reason='changedDuringCheck';continue }
                $record.status='verified';$record.reason='verified';$record.root=$root;$record.executable=$path;$record.version=$version
                $record.runtimeVersion=$runtimeVersion;$record.selectionId=$before
                $record.verificationScope=if ($Tool -eq 'DBeaver') { 'productAndRuntime' } else { 'productFiles' }
                return $record
            } catch {
                if ($_.Exception.ToString() -match 'UnauthorizedAccess|PermissionDenied') { $incomplete=$true;$record.reason='accessDenied' }
                elseif ($_.Exception.Message -eq 'wrongProduct') { $unusable=$true;$record.reason='wrongProduct' }
                else { $incomplete=$true }
            }
        }
        if ($incomplete) { return $record }
        if ($unusable) { return New-SkyviewApplicationLocation $Tool unusable $record.reason }
        return New-SkyviewApplicationLocation $Tool notFound notDiscovered
    } catch { return $record }
}
