# Temporary files only; Windows CI additionally proves actual denied access.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/EditorPreferences.ps1')
$directory=Join-Path ([IO.Path]::GetTempPath()) ('sde editor preferences '+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($directory)
$path=Join-Path $directory 'settings.json'
$node=(Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$nodeRecord=@{version='24.19.0';executable=$node}
$utf8=New-Object Text.UTF8Encoding($false)
$count=0
function Assert-EditorPreference($Condition,[string]$Message) { if (-not $Condition) { throw $Message };$script:count++ }
try {
    foreach ($entry in @(
        @('parser.js','a35db1bfb9631dcba643fa42972e9ebe2a318b4de3cac239d29081577a43d688'),
        @('scanner.js','581d82c4f1aa84b0605369c01f414fb0164ee462e03daa298cb960076a2a9e82'),
        @('LICENSE.md','c3a24c02d678e5f0711623dcf3ab3f243b273c2633f638a1fa8e35fb7c7f8e4d')
    )) {
        $vendor=Join-Path (Join-Path $PSScriptRoot '../windows/chocolatey/tools/jsonc-parser') $entry[0]
        Assert-EditorPreference ((Get-FileHash -LiteralPath $vendor -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $entry[1]) 'Pinned parser/license bytes changed.'
    }
    $record=Get-SkyviewEditorPreferences -NodeObservation $null -SettingsPath $path
    Assert-EditorPreference ($record.status -eq 'missing') 'Missing file was not recognized without a parser.'
    Assert-EditorPreference (-not (Test-Path -LiteralPath $path)) 'A preference check created a file.'
    foreach ($text in @('', '/* keep defaults */', '{"editor.formatOnSave":false,"files.eol":"\r\n",}')) {
        [IO.File]::WriteAllText($path,$text,$utf8)
        $before=(Get-FileHash $path).Hash
        $record=Get-SkyviewEditorPreferences -NodeObservation $nodeRecord -SettingsPath $path
        Assert-EditorPreference ($record.status -eq 'read') 'Valid empty/commented/custom JSONC did not pass inspection.'
        Assert-EditorPreference ((Get-FileHash $path).Hash -ceq $before) 'JSONC bytes changed.'
    }
    Assert-EditorPreference ($record.recommendations[0].status -eq 'different') 'Custom preference was not informational data.'
    [IO.File]::WriteAllText($path,'{"editor.formatOnSave":true,"broken"}',$utf8)
    $record=Get-SkyviewEditorPreferences -NodeObservation $nodeRecord -SettingsPath $path
    Assert-EditorPreference ($record.status -eq 'invalid') 'Fault-tolerant parser supplied a false complete result.'
    Assert-EditorPreference (@($record.recommendations).Count -eq 0) 'Malformed content supplied partial recommendation evidence.'
    $record=Get-SkyviewEditorPreferences -NodeObservation $null -SettingsPath $path
    Assert-EditorPreference ($record.status -eq 'unavailable' -and $record.reason -eq 'parserUnavailable') 'Unavailable parser was mislabeled malformed/missing.'
    [IO.File]::WriteAllText($path,'{}',$utf8)
    $record=Get-SkyviewEditorPreferences -NodeObservation $nodeRecord -SettingsPath $path
    $json=$record | ConvertTo-Json -Compress -Depth 5
    Assert-EditorPreference ($null -ne (ConvertFrom-SkyviewEditorObservation $json $path)) 'Valid evidence was rejected.'
    Assert-EditorPreference ($null -eq (ConvertFrom-SkyviewEditorObservation $json (Join-Path $directory 'other.json'))) 'Another file supplied a verification result.'
    $record | Add-Member -NotePropertyName permission -NotePropertyValue repair
    Assert-EditorPreference ($null -eq (ConvertFrom-SkyviewEditorObservation ($record | ConvertTo-Json -Compress -Depth 5) $path)) 'Injected authority was accepted.'
    if ($env:OS -eq 'Windows_NT' -and $env:GITHUB_ACTIONS -eq 'true') {
        $acl=Get-Acl -LiteralPath $path
        $denied=Get-Acl -LiteralPath $path
        $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
        $rule=New-Object Security.AccessControl.FileSystemAccessRule($sid,[Security.AccessControl.FileSystemRights]::ReadData,[Security.AccessControl.AccessControlType]::Deny)
        $denied.AddAccessRule($rule)
        try {
            Set-Acl -LiteralPath $path -AclObject $denied
            $record=Get-SkyviewEditorPreferences -NodeObservation $nodeRecord -SettingsPath $path
            Assert-EditorPreference ($record.status -eq 'unreadable' -and $record.reason -eq 'accessDenied') 'Denied access was mislabeled missing/invalid.'
        } finally { Set-Acl -LiteralPath $path -AclObject $acl }
    }
    # Run the real extension-list branch with a failed command's partial output.
    $source=Get-Content (Join-Path $PSScriptRoot '../windows/chocolatey/tools/Validate-SkyviewEnvironment.ps1') -Raw
    $start=$source.IndexOf('if (Get-Command codium -ErrorAction SilentlyContinue) {')
    $end=$source.IndexOf('$config = ',$start)
    $fragment=[scriptblock]::Create($source.Substring($start,$end-$start))
    $script:editorFailures=0;$script:editorPasses=0
    function Result($Status,$Message) { if ($Status -eq 'FAIL') { $script:editorFailures++ } }
    function Check($Condition,$Message) { if ($Condition) { $script:editorPasses++ } else { $script:editorFailures++ } }
    $originalCodium=${function:codium}
    try {
        function codium { $global:LASTEXITCODE=7;return 'esbenp.prettier-vscode' }
        & $fragment
        Assert-EditorPreference ($editorFailures -eq 1 -and $editorPasses -eq 0) 'Failed extension listing supplied a partial required pass.'
    } finally {
        if ($originalCodium) { ${function:codium}=$originalCodium } else { Remove-Item Function:codium }
    }
    Write-Host "EDITOR_PREFERENCES_CONTRACTS_OK ($count assertions)"
} finally { [IO.Directory]::Delete($directory,$true) }
$global:LASTEXITCODE=0
