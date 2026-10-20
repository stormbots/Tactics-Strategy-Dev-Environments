# Each fixed read-only query has its own deadline. Never use this for package changes.
function Invoke-SkyviewMetadataQuery {
    param([string[]]$Query)
    $resolved=Get-Command choco -ErrorAction SilentlyContinue
    # Fixture functions are allowed only within read-only contract tests.
    if ($resolved -and $resolved.CommandType -eq 'Function') {
        $rows=@(& choco @Query 2>$null)
        return [pscustomobject]@{Code=$LASTEXITCODE;Rows=$rows;Reason='sourceUnavailable'}
    }
    $exe='C:\ProgramData\chocolatey\bin\choco.exe'
    if (-not (Test-Path -LiteralPath $exe)) { return [pscustomobject]@{Code=1;Rows=@();Reason='sourceUnavailable'} }
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$exe
    $start.Arguments=$Query -join ' '
    $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    $process=New-Object Diagnostics.Process
    $process.StartInfo=$start
    try {
        $null=$process.Start()
        $stdout=$process.StandardOutput.ReadToEndAsync()
        $stderr=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(12000)) {
            $process.Kill(); $process.WaitForExit()
            return [pscustomobject]@{Code=1;Rows=@();Reason='timeout'}
        }
        $text=$stdout.GetAwaiter().GetResult()
        $null=$stderr.GetAwaiter().GetResult()
        if ($text.Length -gt 1000000) { return [pscustomobject]@{Code=1;Rows=@();Reason='incomplete'} }
        return [pscustomobject]@{Code=$process.ExitCode;Rows=@($text -split '[\r\n]+' | Where-Object { $_ });Reason='sourceUnavailable'}
    } catch { return [pscustomobject]@{Code=1;Rows=@();Reason='sourceUnavailable'} }
    finally { $process.Dispose() }
}

# Read-only metadata for the GUI. Package availability is independent of validation.
function Get-SkyviewToolRecords {
    param([hashtable]$Installed, [bool]$CheckUpdates)
    $packages = [ordered]@{Git='git'; 'GitHub CLI'='gh'; 'Node.js'='nodejs-lts'; Python='python314'; VSCodium='vscodium'; DBeaver='dbeaver'; PyCharm='pycharm'; Firefox='firefox'; 'PowerShell 7'='powershell-core'; '7-Zip'='7zip'}
    $candidates = @{}
    $tracked = @{}
    $checked = $false
    if ($CheckUpdates -and ((Get-Command choco -ErrorAction SilentlyContinue) -or (Test-Path 'C:\ProgramData\chocolatey\bin\choco.exe'))) {
        $local = Invoke-SkyviewMetadataQuery -Query @('list','--limit-output')
        $localRows = $local.Rows
        $listOk = $local.Code -eq 0
        foreach ($row in $localRows) {
            $parts = [string]$row -split '\|'
            if ($parts.Count -eq 2) { $tracked[$parts[0]] = $parts[1] }
        }
        $remote = Invoke-SkyviewMetadataQuery -Query @('outdated','--limit-output','--ignore-unfound')
        $rows = $remote.Rows
        $checked = $listOk -and $remote.Code -in @(0,2)
        if ($checked) {
            foreach ($row in $rows) {
                $parts = [string]$row -split '\|'
                if ($parts.Count -ge 3 -and $parts[0] -in $packages.Values) {
                    if ($parts[0] -eq 'nodejs-lts' -and $parts[2] -notmatch '^24\.') { continue }
                    if ($parts[0] -eq 'python314' -and $parts[2] -notmatch '^3\.14\.') { continue }
                    $candidates[$parts[0]] = $parts[2]
                }
            }
        }
    }
    # Node is pinned by design. Resolve the same bounded family as the updater,
    # even when Chocolatey's latest overall release belongs to another major.
    $nodeChecked = $false
    if ($CheckUpdates -and $Installed['Node.js'] -and $tracked.ContainsKey('nodejs-lts')) {
        $nodeQuery = Invoke-SkyviewMetadataQuery -Query @('search','nodejs-lts','--exact','--all-versions','--limit-output','--source=https://community.chocolatey.org/api/v2/')
        $nodeRows = $nodeQuery.Rows
        if ($nodeQuery.Code -eq 0) {
            $versions = @($nodeRows | ForEach-Object { if ($_ -match '^nodejs-lts\|(24\.[0-9]+\.[0-9]+)$') { [version]$Matches[1] } })
            $target = $versions | Sort-Object -Descending | Select-Object -First 1
            if ($target) {
                $nodeChecked = $true
                $candidates.Remove('nodejs-lts')
                if ($Installed['Node.js'] -match '^24\.\d+\.\d+' -and $target -gt [version]$Matches[0]) { $candidates['nodejs-lts'] = $target.ToString() }
            }
        }
    }
    foreach ($tool in @('Git','GitHub CLI','Node.js','Python','VSCodium','DBeaver','PyCharm','Chrome','Firefox','PowerShell 7','OpenSSH','7-Zip','npm')) {
        $current = $Installed[$tool]
        $candidate = $null
        $state = if (-not $packages.Contains($tool)) { 'native' } elseif (-not $CheckUpdates) { 'notChecked' } elseif ($checked) { 'current' } else { 'unavailable' }
        if ($CheckUpdates -and $packages.Contains($tool) -and -not $tracked.ContainsKey($packages[$tool])) { $state = 'unavailable' }
        if ($CheckUpdates -and $tool -eq 'Node.js') { $state = if ($nodeChecked) { 'current' } else { 'unavailable' } }
        if ($state -eq 'current' -and $current -and $packages.Contains($tool) -and $candidates.ContainsKey($packages[$tool])) { $candidate = $candidates[$packages[$tool]] }
        $reason = if ($state -eq 'unavailable') { if ($remote) { $remote.Reason } else { 'sourceUnavailable' } } else { $null }
        if ($tool -eq 'PowerShell 7' -and $state -eq 'current') {
            $executableVersion=$null; $packageVersion=$null; $availableVersion=$null
            $executableOk=[version]::TryParse([string]$current,[ref]$executableVersion)
            $packageOk=[version]::TryParse([string]$tracked['powershell-core'],[ref]$packageVersion)
            if (-not $executableOk -or -not $packageOk) {
                $candidate=$null; $state='unavailable'; $reason='metadataMismatch'
            } else {
                if ($candidate) {
                    if (-not [version]::TryParse([string]$candidate,[ref]$availableVersion)) {
                        $candidate=$null; $state='unavailable'; $reason='incomplete'
                    } elseif ($availableVersion -le $executableVersion) { $candidate=$null }
                }
                if ($state -eq 'current' -and $executableVersion -ne $packageVersion) {
                    $reason='metadataMismatch'
                    if (-not $candidate) { $state='inconsistent' }
                }
            }
        }
        [pscustomobject]@{tool=$tool; installedVersion=$current; availableVersion=$candidate; updateAvailable=[bool]$candidate; updateCheck=$state; updateReason=$reason; source='Chocolatey package metadata'}
    }
}
