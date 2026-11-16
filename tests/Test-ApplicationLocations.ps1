# Read-only/temp-file fixtures. Generated application files are never executed.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/ApplicationLocations.ps1')
$count=0
function Assert-Application($Condition,[string]$Message) { if (-not $Condition) { throw $Message };$script:count++ }
foreach ($tool in @('DBeaver','Chrome','Firefox')) {
    if ($env:OS -eq 'Windows_NT') {
        $search=Get-SkyviewApplicationCandidates $tool
        Assert-Application ($search.Complete -is [bool] -and @($search.Paths).Count -le 12) 'Production discovery exceeded its bound.'
    }
}
function Test-SkyviewEditorOrdinaryUser { return $false }
function Get-SkyviewApplicationCandidates { throw 'Elevated discovery must not run' }
Assert-Application ((Get-SkyviewApplicationLocation Chrome).reason -eq 'normalUserRequired') 'Elevated collection was not refused.'
function Test-SkyviewEditorOrdinaryUser { return $true }
function Get-SkyviewApplicationCandidates { [pscustomobject]@{Paths=@();RequiredPaths=@();Complete=$true} }
Assert-Application ((Get-SkyviewApplicationLocation Firefox).status -eq 'notFound') 'A complete empty search was not distinguished.'
function Get-SkyviewApplicationCandidates { [pscustomobject]@{Paths=@();RequiredPaths=@();Complete=$false} }
Assert-Application ((Get-SkyviewApplicationLocation Firefox).status -eq 'incomplete') 'An incomplete search claimed absence.'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/ToolRecords.ps1')
function Invoke-SkyviewMetadataQuery { [pscustomobject]@{Code=0;Rows=@();Reason='completed'} }
foreach ($tool in @('DBeaver','Chrome','Firefox')) {
    $record=Get-SkyviewToolRecords -Installed @{$tool='26.2.1'} -CheckUpdates $true | Where-Object tool -eq $tool
    Assert-Application ($record.updateReason -eq 'applicationMaintenanceUnverified' -and -not $record.updateAvailable) 'Usability granted update ownership.'
}
if ($env:OS -ne 'Windows_NT') {
    # Test-only Unix path adapter for PE/resource fixtures. Windows CI uses the
    # production local-drive/reparse guard without this adapter.
    function Get-SkyviewEditorFile($Path,$Maximum) {
        $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if ($item.PSIsContainer -or $item.Length -gt $Maximum) { throw 'inspectionLimit' }
        return $item
    }
}
& {
    $directory=Join-Path ([IO.Path]::GetTempPath()) ('sde alternate applications '+[guid]::NewGuid().ToString('N'))
    $null=[IO.Directory]::CreateDirectory($directory)
    $utf8=New-Object Text.UTF8Encoding($false)
    $paths=@{}
    try {
        foreach ($tool in @('Chrome','Firefox')) {
            $root=Join-Path $directory $tool;$null=[IO.Directory]::CreateDirectory($root)
            $path=Join-Path $root ($tool.ToLowerInvariant()+'.exe');$paths[$tool]=$path
            $product=if ($tool -eq 'Chrome') { 'Google Chrome' } else { 'Firefox' }
            $version=if ($tool -eq 'Chrome') { '143.0.7499.40' } else { '146.0.1.0' }
            $displayVersion=if ($tool -eq 'Firefox') { $version+'esr' } else { $version }
            # Compile version resources for real FileVersionInfo inspection only.
            $definition="using System.Reflection; [assembly: AssemblyProduct(`"$product`")] [assembly: AssemblyFileVersion(`"$version`")] [assembly: AssemblyInformationalVersion(`"$displayVersion`")] public class $($tool)LocationFixture {}"
            Add-Type -TypeDefinition $definition -OutputAssembly $path -OutputType Library
            if ($tool -eq 'Firefox') {
                [IO.File]::WriteAllText((Join-Path $root 'application.ini'),"[App]`nName=Firefox`nID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}`nVersion=$version`n",$utf8)
            }
        }
        $dbeaver=Join-Path $directory 'DBeaver';$null=[IO.Directory]::CreateDirectory((Join-Path $dbeaver 'jre/bin'))
        $null=[IO.Directory]::CreateDirectory((Join-Path $dbeaver 'plugins'))
        $paths.DBeaver=Join-Path $dbeaver 'dbeaver.exe'
        $bytes=New-Object byte[] 70;$bytes[0]=0x4d;$bytes[1]=0x5a;$bytes[60]=64;$bytes[64]=0x50;$bytes[65]=0x45;$bytes[68]=0x64;$bytes[69]=0x86
        foreach ($file in @($paths.DBeaver,(Join-Path $dbeaver 'jre/bin/java.exe'),(Join-Path $dbeaver 'jre/bin/javaw.exe'))) { [IO.File]::WriteAllBytes($file,$bytes) }
        [IO.File]::WriteAllText((Join-Path $dbeaver '.eclipseproduct'),"name=DBeaver`nid=org.jkiss.dbeaver.product`nversion=26.2.1`n",$utf8)
        [IO.File]::WriteAllText((Join-Path $dbeaver 'dbeaver.ini'),"-startup`nplugins/org.jkiss.dbeaver.launcher_1.0.0.jar`n-vmargs`n-Dosgi.requiredJavaVersion=21`n",$utf8)
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $jar=Join-Path $dbeaver 'plugins/org.jkiss.dbeaver.launcher_1.0.0.jar'
        $archive=[IO.Compression.ZipFile]::Open($jar,[IO.Compression.ZipArchiveMode]::Create)
        try {
            $entry=$archive.CreateEntry('META-INF/MANIFEST.MF');$stream=$entry.Open()
            try { $data=[Text.Encoding]::UTF8.GetBytes("Bundle-SymbolicName: org.jkiss.dbeaver.launcher;singleton:=true`n");$stream.Write($data,0,$data.Length) }
            finally { $stream.Dispose() }
        } finally { $archive.Dispose() }
        $script:applicationPaths=$paths;$script:applicationCode=0;$script:applicationText='openjdk 21.0.9 2025-10-21'
        $script:applicationCalls=New-Object 'System.Collections.Generic.List[object]'
        function Get-SkyviewApplicationCandidates($Tool) { [pscustomobject]@{Paths=@($script:applicationPaths[$Tool]);RequiredPaths=@($script:applicationPaths[$Tool]);Complete=$true} }
        function Invoke-SkyviewEditorQuery($Executable,$Arguments,$TimeoutMs) {
            if ($Executable -cne (Join-Path (Split-Path $script:applicationPaths.DBeaver -Parent) 'jre\bin\java.exe') -or $Arguments[0] -cne '--version') { throw 'A browser/IDE or another runtime was executed.' }
            $script:applicationCalls.Add($Executable)
            return @{Code=$script:applicationCode;Text=$script:applicationText}
        }
        foreach ($tool in @('DBeaver','Chrome','Firefox')) {
            $before=(Get-FileHash -LiteralPath $paths[$tool]).Hash
            $record=Get-SkyviewApplicationLocation $tool
            Assert-Application ($record.status -eq 'verified' -and $record.executable -ceq $paths[$tool]) ("Alternate $tool installation did not verify: "+($record | ConvertTo-Json -Compress))
            Assert-Application ($record.maintenanceEligibility -eq 'notEvaluated') 'Readiness granted update permission.'
            Assert-Application ((Get-FileHash -LiteralPath $paths[$tool]).Hash -ceq $before) 'Inspection changed an application.'
        }
        Assert-Application ($applicationCalls.Count -eq 1) 'Browser/IDE collection executed a GUI application.'
        $script:applicationCode=7
        Assert-Application ((Get-SkyviewApplicationLocation DBeaver).status -eq 'unusable') 'Failed Java output passed.'
        $script:applicationCode=0;$script:applicationText='openjdk 17.0.9'
        Assert-Application ((Get-SkyviewApplicationLocation DBeaver).status -eq 'unusable') 'Java below the product requirement passed.'
        $script:applicationText='openjdk 21.0.9'
        [IO.File]::WriteAllText((Join-Path $dbeaver '.eclipseproduct'),"name=Other`nid=org.jkiss.dbeaver.product`nversion=26.2.1`n",$utf8)
        $calls=$applicationCalls.Count
        Assert-Application ((Get-SkyviewApplicationLocation DBeaver).status -eq 'unusable') 'Wrong product passed.'
        Assert-Application ($applicationCalls.Count -eq $calls) 'Wrong product ran a runtime query.'
        [IO.File]::WriteAllText((Join-Path (Split-Path $paths.Firefox -Parent) 'application.ini'),"[App]`nName=Firefox`nID=wrong`nVersion=146.0.1.0`n",$utf8)
        Assert-Application ((Get-SkyviewApplicationLocation Firefox).status -eq 'unusable') 'Wrong Firefox identity passed.'
        [IO.File]::Delete($paths.Chrome)
        $record=Get-SkyviewApplicationLocation Chrome
        Assert-Application ($record.status -eq 'incomplete' -and $record.reason -eq 'staleRegistration') 'Stale registration was reported absent.'
    } finally { [IO.Directory]::Delete($directory,$true) }
}
Write-Host "APPLICATION_LOCATION_CONTRACTS_OK ($count assertions)"
$global:LASTEXITCODE=0
