# Temporary-file/read-only contracts. Fake executables are never launched.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/EditorLocation.ps1')
$count=0
function Assert-EditorLocation($Condition,[string]$Message) { if (-not $Condition) { throw $Message };$script:count++ }
if ($env:OS -eq 'Windows_NT') {
    $actualCandidates=Get-SkyviewEditorCandidates
    Assert-EditorLocation ($actualCandidates.Complete -is [bool] -and @($actualCandidates.Paths).Count -le 12) 'Production registry/PATH discovery did not return a bounded search.'
}
$node=(Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$probe=Join-Path $PSScriptRoot '../windows/chocolatey/tools/EditorIdentityProbe.cjs'
$query=Invoke-SkyviewEditorQuery $node @('-e','console.log(process.env.ELECTRON_RUN_AS_NODE+":"+String(process.env.NODE_OPTIONS))') 2000
Assert-EditorLocation ($query.Code -eq 0 -and $query.Text -ceq '1:undefined') 'Read-only query did not set the bundled-runtime mode.'
$query=Invoke-SkyviewEditorQuery $node @('-e','console.log("x".repeat(40000))') 2000
Assert-EditorLocation ($query.Code -eq -1) 'Oversized diagnostic output was accepted.'
$query=Invoke-SkyviewEditorQuery $node @('-e','setTimeout(()=>{},5000)') 100
Assert-EditorLocation ($query.Code -eq -1) 'Diagnostic deadline was ignored.'
$query=Invoke-SkyviewEditorQuery $node @($probe) 2000
Assert-EditorLocation ($query.Code -ne 0 -and -not $query.Text) 'Ordinary Node supplied Electron identity.'
$query=Invoke-SkyviewEditorQuery (Join-Path ([IO.Path]::GetTempPath()) 'missing-sde-editor.exe') @() 2000
Assert-EditorLocation ($query.Code -eq -1) 'Failed process creation did not stay incomplete.'

function Test-SkyviewEditorOrdinaryUser { return $false }
function Get-SkyviewEditorCandidates { throw 'must not discover with an elevated token' }
$value=Get-SkyviewEditorLocation
Assert-EditorLocation ($value.status -eq 'incomplete' -and $value.reason -eq 'normalUserRequired') 'Elevated role executed discovery.'
function Test-SkyviewEditorOrdinaryUser { return $true }
function Get-SkyviewEditorCandidates { [pscustomobject]@{Paths=@();RequiredPaths=@();Complete=$true} }
$value=Get-SkyviewEditorLocation
Assert-EditorLocation ($value.status -eq 'notFound') 'A complete empty search did not report notFound.'
function Get-SkyviewEditorCandidates { [pscustomobject]@{Paths=@();RequiredPaths=@();Complete=$false} }
$value=Get-SkyviewEditorLocation
Assert-EditorLocation ($value.status -eq 'incomplete') 'An incomplete search claimed absence.'

# Windows-native checks use actual paths/files and the real CJS snapshot function.
if ($env:OS -eq 'Windows_NT') {
    $directory=Join-Path ([IO.Path]::GetTempPath()) ('sde editor location '+[guid]::NewGuid().ToString('N'))
    $utf8=New-Object Text.UTF8Encoding($false)
    $null=[IO.Directory]::CreateDirectory((Join-Path $directory 'resources/app/out'))
    $exe=Join-Path $directory 'VSCodium.exe'
    $cli=Join-Path $directory 'resources/app/out/cli.js'
    $bytes=New-Object byte[] 68
    $bytes[0]=0x4d; $bytes[1]=0x5a; $bytes[60]=64; $bytes[64]=0x50; $bytes[65]=0x45
    [IO.File]::WriteAllBytes($exe,$bytes)
    [IO.File]::WriteAllText((Join-Path $directory 'resources/app/product.json'),'{"nameShort":"VSCodium","applicationName":"codium","quality":"stable"}',$utf8)
    [IO.File]::WriteAllText((Join-Path $directory 'resources/app/package.json'),'{"version":"1.106.0.25351"}',$utf8)
    [IO.File]::WriteAllText($cli,'// fixture, never executed',$utf8)
    try {
        $version=Test-SkyviewEditorLayout $exe
        Assert-EditorLocation ($version -ceq '1.106.0.25351') 'Alternate supported layout was rejected.'
        $snapshot=Join-Path $directory 'fixture-snapshot.cjs'
        [IO.File]::WriteAllText($snapshot,'console.log(JSON.stringify(require(process.argv[2]).snapshot(process.argv[3], "38.0.0")))',$utf8)
        $text=& $node $snapshot $probe $exe
        Assert-EditorLocation ($LASTEXITCODE -eq 0) 'CJS fixture snapshot failed.'
        $record=ConvertFrom-SkyviewEditorLocation $text $exe $version
        Assert-EditorLocation ($null -ne $record) 'CJS and PowerShell fingerprints disagree.'
        $before=(Get-FileHash $exe).Hash
        $script:editorFixture=$record
        $script:editorVersionCode=0
        $script:editorVersionText=$version
        $script:editorQueries=New-Object 'System.Collections.Generic.List[object]'
        function Get-SkyviewEditorCandidates { [pscustomobject]@{Paths=@($script:editorFixture.executable);RequiredPaths=@($script:editorFixture.executable);Complete=$true} }
        function Invoke-SkyviewEditorQuery($Executable,$Arguments,$TimeoutMs) {
            $script:editorQueries.Add(@{Executable=$Executable;Arguments=$Arguments})
            if ($Arguments[-1] -eq '--version') { return @{Code=$script:editorVersionCode;Text=$script:editorVersionText} }
            return @{Code=0;Text=($script:editorFixture | ConvertTo-Json -Compress)}
        }
        $value=Get-SkyviewEditorLocation
        Assert-EditorLocation ($value.status -eq 'verified' -and $value.selectionId -ceq $record.selectionId) 'The selected installation was not verified.'
        Assert-EditorLocation ($editorQueries.Count -eq 2 -and $editorQueries[1].Executable -ceq $record.executable -and $editorQueries[1].Arguments[0] -ceq $record.cli) 'Version query used a different installation.'
        foreach ($case in @(@(7,$version),@(0,'not a version'),@(0,'1.100.0'),@(-1,''))) {
            $script:editorVersionCode=$case[0];$script:editorVersionText=$case[1]
            $value=Get-SkyviewEditorLocation
            Assert-EditorLocation ($value.status -ne 'verified' -and $null -eq $value.selectionId) 'Failed or mismatched version passed.'
        }
        $script:editorVersionCode=0;$script:editorVersionText=$version
        $record | Add-Member -NotePropertyName permission -NotePropertyValue update
        Assert-EditorLocation ($null -eq (ConvertFrom-SkyviewEditorLocation ($record | ConvertTo-Json -Compress) $exe $version)) 'Injected authority was accepted.'
        $record.PSObject.Properties.Remove('permission')
        $old=Get-SkyviewEditorFingerprint $record.executable
        [IO.File]::WriteAllText($cli,'changed',$utf8)
        Assert-EditorLocation ((Get-SkyviewEditorFingerprint $record.executable) -cne $old) 'Changed resource retained its selection ID.'
        Assert-EditorLocation ($null -eq (ConvertFrom-SkyviewEditorLocation $text $exe $version)) 'Stale identity remained verified.'
        if ($env:GITHUB_ACTIONS -eq 'true') {
            $acl=Get-Acl -LiteralPath $exe
            $denied=Get-Acl -LiteralPath $exe
            $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
            $rule=New-Object Security.AccessControl.FileSystemAccessRule($sid,[Security.AccessControl.FileSystemRights]::ReadData,[Security.AccessControl.AccessControlType]::Deny)
            $denied.AddAccessRule($rule)
            try {
                Set-Acl -LiteralPath $exe -AclObject $denied
                $value=Get-SkyviewEditorLocation
                Assert-EditorLocation ($value.status -eq 'incomplete' -and $value.reason -eq 'accessDenied') 'Denied access was mislabeled absent or unusable.'
            } finally { Set-Acl -LiteralPath $exe -AclObject $acl }
        }
        [IO.File]::WriteAllText((Join-Path $directory 'resources/app/product.json'),'{"nameShort":"Other"}',$utf8)
        $rejected=$false
        try { $null=Test-SkyviewEditorLayout $exe } catch { $rejected=$true }
        Assert-EditorLocation $rejected 'A different product passed static verification.'
        Assert-EditorLocation ((Get-FileHash $exe).Hash -ceq $before) 'Inspection wrote the executable.'
        function Get-SkyviewEditorCandidates { [pscustomobject]@{Paths=@('C:\missing-sde-editor\VSCodium.exe');RequiredPaths=@('C:\missing-sde-editor\VSCodium.exe');Complete=$true} }
        $value=Get-SkyviewEditorLocation
        Assert-EditorLocation ($value.status -eq 'incomplete' -and $value.reason -eq 'staleRegistration') 'Stale registration was mislabeled absent.'
    } finally { [IO.Directory]::Delete($directory,$true) }
}
# Exercise the required-check function with a failed command's partial output.
function Get-SkyviewEditorFile { return $null }
function Get-SkyviewEditorFingerprint { return ('a'*64) }
function Invoke-SkyviewEditorQuery { return @{Code=7;Text='esbenp.prettier-vscode'} }
$checks=@(Get-SkyviewEditorRequiredChecks ([pscustomobject]@{status='verified';version='1.106.0';executable='fixture';cli='fixture';selectionId=('a'*64)}))
Assert-EditorLocation (@($checks | Where-Object Status -eq FAIL).Count -eq 1) 'Failed extension listing lost its failure.'
Assert-EditorLocation (@($checks | Where-Object { $_.Status -eq 'PASS' -and $_.Message -match 'extension' }).Count -eq 0) 'Failed extension listing supplied partial extension passes.'
Write-Host "EDITOR_LOCATION_CONTRACTS_OK ($count assertions)"
$global:LASTEXITCODE=0
