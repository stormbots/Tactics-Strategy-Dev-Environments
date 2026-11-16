# Temporary fixtures only. A fixture launcher/runtime is never executed.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/PyCharmLocation.ps1')
$count=0
function Assert-PyCharm($Condition,[string]$Message) { if (-not $Condition) { throw $Message };$script:count++ }
if ($env:OS -eq 'Windows_NT') {
    $actual=Get-SkyviewPyCharmCandidates
    Assert-PyCharm ($actual.Complete -is [bool] -and @($actual.Roots).Count -le 12) 'Production discovery was not bounded.'
}
function Test-SkyviewEditorOrdinaryUser { return $false }
function Get-SkyviewPyCharmCandidates { throw 'Elevated discovery must not run' }
Assert-PyCharm ((Get-SkyviewPyCharmLocation).reason -eq 'normalUserRequired') 'Elevated use was not refused.'
function Test-SkyviewEditorOrdinaryUser { return $true }
function Get-SkyviewPyCharmCandidates { [pscustomobject]@{Roots=@();RequiredRoots=@();Complete=$true} }
Assert-PyCharm ((Get-SkyviewPyCharmLocation).status -eq 'notFound') 'Empty complete search was not distinguished.'
function Get-SkyviewPyCharmCandidates { [pscustomobject]@{Roots=@();RequiredRoots=@();Complete=$false} }
Assert-PyCharm ((Get-SkyviewPyCharmLocation).status -eq 'incomplete') 'Incomplete search claimed absence.'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/ToolRecords.ps1')
function Invoke-SkyviewMetadataQuery { [pscustomobject]@{Code=0;Rows=@();Reason='completed'} }
$metadataRecord=Get-SkyviewToolRecords -Installed @{PyCharm='2026.1.1'} -CheckUpdates $true | Where-Object tool -eq PyCharm
Assert-PyCharm ($metadataRecord.installedVersion -eq '2026.1.1' -and $metadataRecord.updateReason -eq 'applicationMaintenanceUnverified' -and -not $metadataRecord.updateAvailable) 'Selected usability granted package update authority.'
if ($env:OS -eq 'Windows_NT') {
    $directory=Join-Path ([IO.Path]::GetTempPath()) ('sde PyCharm alternate '+[guid]::NewGuid().ToString('N'))
    $null=[IO.Directory]::CreateDirectory((Join-Path $directory 'bin'))
    $null=[IO.Directory]::CreateDirectory((Join-Path $directory 'jbr/bin'))
    $utf8=New-Object Text.UTF8Encoding($false)
    $metadata=Join-Path $directory 'product-info.json'
    $launcher=Join-Path $directory 'bin/pycharm64.exe'
    $runtime=Join-Path $directory 'jbr/bin/java.exe'
    $bytes=New-Object byte[] 70
    $bytes[0]=0x4d;$bytes[1]=0x5a;$bytes[60]=64;$bytes[64]=0x50;$bytes[65]=0x45
    $bytes[68]=0x64;$bytes[69]=0x86
    [IO.File]::WriteAllBytes($launcher,$bytes);[IO.File]::WriteAllBytes($runtime,$bytes)
    $info=@{name='PyCharm';productCode='PY';version='2026.1.1';minRequiredJavaVersion=21;launch=@(@{os='Windows';arch='amd64';launcherPath='bin/pycharm64.exe';javaExecutablePath='jbr/bin/java.exe'})}
    [IO.File]::WriteAllText($metadata,($info | ConvertTo-Json -Depth 5),$utf8)
    $script:pycharmRoot=$directory;$script:pycharmRuntime=$runtime;$script:pycharmCode=0
    $script:pycharmText="openjdk 21.0.7 2025-04-15`nOpenJDK Runtime Environment JBR-21.0.7+6"
    $script:pycharmCalls=New-Object 'System.Collections.Generic.List[object]'
    function Get-SkyviewPyCharmCandidates { [pscustomobject]@{Roots=@($script:pycharmRoot);RequiredRoots=@($script:pycharmRoot);Complete=$true} }
    function Invoke-SkyviewEditorQuery($Executable,$Arguments,$TimeoutMs) {
        if ($Executable -cne $script:pycharmRuntime -or $Arguments.Count -ne 1 -or $Arguments[0] -cne '--version') { throw 'Wrong runtime/arguments' }
        $script:pycharmCalls.Add($Executable)
        return @{Code=$script:pycharmCode;Text=$script:pycharmText}
    }
    try {
        $before=(Get-FileHash $launcher).Hash
        $record=Get-SkyviewPyCharmLocation
        Assert-PyCharm ($record.status -eq 'verified' -and $record.version -eq '2026.1.1') 'Alternate bundle did not verify.'
        Assert-PyCharm ($record.runtime -ceq $runtime -and $record.launcher -ceq $launcher -and $pycharmCalls.Count -eq 1) 'The selected bundle did not own its runtime probe.'
        Assert-PyCharm ($record.maintenanceEligibility -eq 'notEvaluated') 'Usability granted maintenance permission.'
        foreach ($code in @(7,-1)) {
            $script:pycharmCode=$code
            $record=Get-SkyviewPyCharmLocation
            Assert-PyCharm ($record.status -ne 'verified' -and $null -eq $record.root) 'Failed runtime returned a successful selection.'
        }
        $script:pycharmCode=0;$script:pycharmText="openjdk 17.0.9`nJBR-17"
        Assert-PyCharm ((Get-SkyviewPyCharmLocation).status -eq 'unusable') 'A runtime below the product minimum passed.'
        $script:pycharmCode=0;$script:pycharmText='not a runtime'
        Assert-PyCharm ((Get-SkyviewPyCharmLocation).status -ne 'verified') 'Unrecognized runtime was accepted.'
        $script:pycharmText="openjdk 21.0.7`nJBR-21"
        $info.productCode='IU'
        [IO.File]::WriteAllText($metadata,($info | ConvertTo-Json -Depth 5),$utf8)
        $calls=$pycharmCalls.Count
        Assert-PyCharm ((Get-SkyviewPyCharmLocation).status -eq 'unusable') 'Wrong product was accepted.'
        Assert-PyCharm ($pycharmCalls.Count -eq $calls) 'Wrong product triggered runtime execution.'
        $info.productCode='PC';$info.name='PyCharm Community Edition'
        [IO.File]::WriteAllText($metadata,($info | ConvertTo-Json -Depth 5),$utf8)
        Assert-PyCharm ((Get-SkyviewPyCharmLocation).status -eq 'verified') 'Supported community edition failed.'
        $layout=Get-SkyviewPyCharmLayout $directory
        $id=Get-SkyviewPyCharmFingerprint $layout
        [IO.File]::WriteAllBytes($runtime,($bytes+[byte]1))
        Assert-PyCharm ((Get-SkyviewPyCharmFingerprint $layout) -cne $id) 'Changed runtime retained its fingerprint.'
        Assert-PyCharm ((Get-FileHash $launcher).Hash -ceq $before) 'Inspection changed the launcher.'
        [IO.File]::Delete($runtime)
        Assert-PyCharm ((Get-SkyviewPyCharmLocation).status -eq 'incomplete') 'Disappearance was mislabeled absent.'
    } finally { [IO.Directory]::Delete($directory,$true) }
}
Write-Host "PYCHARM_LOCATION_CONTRACTS_OK ($count assertions)"
$global:LASTEXITCODE=0
