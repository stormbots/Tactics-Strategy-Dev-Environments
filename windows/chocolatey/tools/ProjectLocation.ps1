# Working-folder evidence only. No remote identity, Save, trust or mutation authority.
. (Join-Path $PSScriptRoot 'EditorLocation.ps1')
function Get-SkyviewProjectLocation([string]$Path) {
    $result=[pscustomobject][ordered]@{schema=1;status='incomplete';reason='inspectionIncomplete';root=$null}
    if (-not (Test-SkyviewEditorOrdinaryUser)) { $result.reason='normalUserRequired';return $result }
    if (-not $Path -or $Path.Length -gt 4096 -or $Path -notmatch '\A[A-Za-z]:[\\/]' -or $Path -match '[\x00-\x1f\x7f|\u202a-\u202e\u2066-\u2069]') { $result.reason='unsupportedPath';return $result }
    try {
        $directory=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if (-not $directory.PSIsContainer) { $result.reason='notDirectory';return $result }
        $part=$directory
        while ($part) {
            if ($part.Attributes -band [IO.FileAttributes]::ReparsePoint) { $result.reason='unsupportedPath';return $result }
            $part=$part.Parent
        }
        $git=Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $git) { $result.reason='gitUnavailable';return $result }
        $remove=@([Environment]::GetEnvironmentVariables().Keys | Where-Object { $_ -like 'GIT_*' -and $_ -notin @('GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_CONFIG_NOSYSTEM') })
        $probe=Invoke-SkyviewEditorQuery $git.Source @('--no-pager','--no-optional-locks','-C',$directory.FullName,'-c','core.fsmonitor=false','rev-parse','--show-toplevel','--is-inside-work-tree') 6000 $remove
        if ($probe.Code -ne 0) { return $result }
        $rows=@($probe.Text -split '\r?\n')
        if ($rows.Count -ne 2 -or $rows[1] -cne 'true' -or $rows[0] -notmatch '\A[A-Za-z]:[\\/]' -or $rows[0] -match '[\x00-\x1f\x7f|]') { return $result }
        $reported=Get-Item -LiteralPath $rows[0] -Force -ErrorAction Stop
        if (-not [string]::Equals($directory.FullName.TrimEnd('\'),$reported.FullName.TrimEnd('\'),[StringComparison]::OrdinalIgnoreCase)) { $result.reason='rootMismatch';return $result }
        $result.status='verified';$result.reason='verified';$result.root=$directory.FullName
        return $result
    } catch { $result.reason='locationUnavailable';return $result }
}
