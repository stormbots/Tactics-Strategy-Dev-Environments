# Optional user-file observations only. No writer or native execution permission.
. (Join-Path $PSScriptRoot 'NodeRuntime.ps1')
function New-SkyviewEditorObservation($Path,[string]$Status='unavailable',[string]$Reason='parserUnavailable') {
    return @{schema=1;component='VSCodium';scope='standardUserFile';path=$Path;status=$Status;reason=$Reason;recommendations=@()}
}
function ConvertFrom-SkyviewEditorObservation([string]$Text,[string]$Path) {
    try {
        $value=$Text | ConvertFrom-Json -ErrorAction Stop
        $names=(@($value.PSObject.Properties.Name) | Sort-Object) -join ','
        if ($names -cne 'component,path,reason,recommendations,schema,scope,status' -or
            ($value.schema -isnot [int] -and $value.schema -isnot [long]) -or $value.schema -ne 1 -or
            $value.component -cne 'VSCodium' -or $value.scope -cne 'standardUserFile' -or $value.path -cne $Path) { return $null }
        $reasons=@{read=@('verified');missing=@('defaults');unreadable=@('accessDenied','readFailed');invalid=@('invalidContents');unavailable=@('parserUnavailable','inspectionLimit','locationUnavailable','encodingUnavailable')}
        if (@('read','missing','unreadable','invalid','unavailable') -cnotcontains $value.status -or $reasons[$value.status] -cnotcontains $value.reason -or $value.recommendations -isnot [array]) { return $null }
        $rows=@($value.recommendations)
        if ($value.status -cne 'read') { if ($rows.Count -eq 0) { return $value }; return $null }
        if ($rows.Count -ne 3) { return $null }
        $expected=@(@{key='editor.formatOnSave';recommended=$true},@{key='editor.defaultFormatter';recommended='esbenp.prettier-vscode'},@{key='files.eol';recommended="`n"})
        for ($index=0;$index -lt 3;$index++) {
            $row=$rows[$index]
            if (((@($row.PSObject.Properties.Name) | Sort-Object) -join ',') -cne 'key,recommended,status,value' -or
                $row.key -cne $expected[$index].key -or
                ($row.recommended | ConvertTo-Json -Compress) -cne ($expected[$index].recommended | ConvertTo-Json -Compress) -or
                @('matches','different','unset') -cnotcontains $row.status -or
                ($null -ne $row.value -and $row.value -isnot [bool] -and ($row.value -isnot [string] -or $row.value.Length -gt 256))) { return $null }
            $matchesValue=($row.value | ConvertTo-Json -Compress) -ceq ($expected[$index].recommended | ConvertTo-Json -Compress)
            if (($row.status -ceq 'matches') -ne $matchesValue -or ($row.status -ceq 'unset' -and $null -ne $row.value)) { return $null }
        }
        return $value
    } catch { return $null }
}
function Get-SkyviewEditorPreferences {
    param($NodeObservation,[string]$SettingsPath)
    if (-not $SettingsPath -and $env:APPDATA) { $SettingsPath=Join-Path $env:APPDATA 'VSCodium\User\settings.json' }
    if (-not $SettingsPath -or $SettingsPath.Length -gt 4096 -or -not [IO.Path]::IsPathRooted($SettingsPath) -or $SettingsPath -match '[\x00-\x1f\x7f|]') {
        return New-SkyviewEditorObservation $null unavailable locationUnavailable
    }
    $fallback=New-SkyviewEditorObservation $SettingsPath
    try {
        if ([IO.File]::GetAttributes($SettingsPath) -band [IO.FileAttributes]::Directory) { return New-SkyviewEditorObservation $SettingsPath unreadable readFailed }
        $stream=[IO.File]::Open($SettingsPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
        try { $length=$stream.Length;$null=$stream.ReadByte() } finally { $stream.Dispose() }
        if ($length -gt 1048576) { return New-SkyviewEditorObservation $SettingsPath unavailable inspectionLimit }
    } catch {
        $problem=$_.Exception
        if ($problem.InnerException) { $problem=$problem.InnerException }
        if ($problem -is [IO.FileNotFoundException] -or $problem -is [IO.DirectoryNotFoundException]) { return New-SkyviewEditorObservation $SettingsPath missing defaults }
        if ($problem -is [UnauthorizedAccessException]) { return New-SkyviewEditorObservation $SettingsPath unreadable accessDenied }
        return New-SkyviewEditorObservation $SettingsPath unreadable readFailed
    }
    try {
        if (-not $NodeObservation -or $NodeObservation.version -notmatch '\A24\.\d{1,8}\.\d{1,8}\z' -or
            -not [IO.Path]::IsPathRooted($NodeObservation.executable) -or -not [IO.File]::Exists($NodeObservation.executable)) { return $fallback }
        $probe=Invoke-SkyviewNodeQuery $NodeObservation.executable @((Join-Path $PSScriptRoot 'EditorSettingsProbe.cjs'),$SettingsPath) 2500
        if ($probe.Code -eq 0) {
            $record=ConvertFrom-SkyviewEditorObservation $probe.Text $SettingsPath
            if ($record) { return $record }
        }
    } catch { return $fallback }
    return $fallback
}
