# Read-only metadata for the GUI. Package availability is independent of validation.
function Get-SkyviewToolRecords {
    param([hashtable]$Installed, [bool]$CheckUpdates)
    $packages = [ordered]@{Git='git'; 'GitHub CLI'='gh'; 'Node.js'='nodejs-lts'; Python='python314'; VSCodium='vscodium'; DBeaver='dbeaver'; PyCharm='pycharm'; Firefox='firefox'; 'PowerShell 7'='powershell-core'; '7-Zip'='7zip'}
    $candidates = @{}
    $tracked = @{}
    $checked = $false
    if ($CheckUpdates -and (Get-Command choco -ErrorAction SilentlyContinue)) {
        $localRows = @(& choco list --limit-output 2>$null)
        $listOk = $LASTEXITCODE -eq 0
        foreach ($row in $localRows) {
            $parts = [string]$row -split '\|'
            if ($parts.Count -eq 2) { $tracked[$parts[0]] = $parts[1] }
        }
        $rows = @(& choco outdated --limit-output --ignore-unfound 2>$null)
        $checked = $listOk -and $LASTEXITCODE -in @(0,2)
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
        $nodeRows = @(& choco search nodejs-lts --exact --all-versions --limit-output --source=https://community.chocolatey.org/api/v2/ 2>$null)
        if ($LASTEXITCODE -eq 0) {
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
        [pscustomobject]@{tool=$tool; installedVersion=$current; availableVersion=$candidate; updateAvailable=[bool]$candidate; updateCheck=$state}
    }
}
