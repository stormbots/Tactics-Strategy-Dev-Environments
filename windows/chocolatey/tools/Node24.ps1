# Shared install/update policy. Loading this file performs no provisioning.
function Get-SkyviewNode24Plan {
    param([hashtable]$Packages, [string[]]$RegisteredVersions)
    $remove = @()
    foreach ($id in @('nodejs', 'nodejs.install')) {
        if ($Packages.ContainsKey($id)) { $remove += $id }
    }
    if ($Packages.ContainsKey('nodejs-lts') -and ([version]$Packages['nodejs-lts']).Major -ne 24) {
        $remove += 'nodejs-lts'
    }
    foreach ($version in $RegisteredVersions) {
        $managed = @('nodejs.install', 'nodejs-lts') | Where-Object {
            $Packages.ContainsKey($_) -and ([version]$Packages[$_] -eq [version]$version)
        }
        if (([version]$version).Major -ne 24 -and -not $managed) {
            throw "Node.js $version is not tracked by Chocolatey. Remove or switch that runtime to Node 24, then retry."
        }
        if ($remove.Count -and -not $managed) {
            throw "Node.js $version does not match Chocolatey's records. Resolve the runtime mismatch before retrying."
        }
    }
    return ,$remove
}

function Invoke-SkyviewNodeChocolatey {
    param([string]$Chocolatey, [string[]]$Arguments)
    & $Chocolatey @Arguments | ForEach-Object { Write-Host $_ }
    $code = $LASTEXITCODE
    if ($code -notin @(0, 1605, 1614, 1641, 3010)) {
        throw "Node.js setup stopped (Chocolatey exit $code). Resolve the reported package error and retry; no forced dependency removal is used."
    }
}

function Install-SkyviewNode24 {
    param([string]$Version)
    $choco = 'C:\ProgramData\chocolatey\bin\choco.exe'
    if (-not (Test-Path $choco)) { throw 'Chocolatey executable not found.' }
    $rows = @(& $choco list --limit-output)
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect installed Chocolatey packages.' }
    $packages = @{}
    foreach ($row in $rows) {
        if ($row -match '^(nodejs|nodejs\.install|nodejs-lts)\|([0-9.]+)$') { $packages[$Matches[1]] = $Matches[2] }
    }
    # Read the uninstall registry, never Win32_Product (which can repair MSIs).
    $registered = @(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -eq 'Node.js' } | ForEach-Object { $_.DisplayVersion })
    $remove = Get-SkyviewNode24Plan -Packages $packages -RegisteredVersions $registered
    if (-not $Version) {
        $available = @(& $choco search nodejs-lts --exact --all-versions --limit-output --source=https://community.chocolatey.org/api/v2/)
        if ($LASTEXITCODE -ne 0) { throw 'Could not resolve Node 24 before changing the installed runtime.' }
        $versions = foreach ($row in $available) {
            if ($row -match '^nodejs-lts\|(24\.[0-9]+\.[0-9]+)$') { [version]$Matches[1] }
        }
        $target = $versions | Sort-Object -Descending | Select-Object -First 1
        if (-not $target) { throw 'No approved Node 24 package was found; the installed runtime was preserved.' }
        $Version = $target.ToString()
    }
    if (([version]$Version).Major -ne 24) { throw "Refusing Node.js $Version; this baseline requires Node 24." }
    Write-Host "SKYVIEW_EVENT|phase|node24|Configuring the approved Node.js $Version runtime"
    foreach ($id in $remove) {
        $current = @(& $choco list --limit-output)
        if ($LASTEXITCODE -ne 0) { throw 'Could not recheck the runtime package before migration.' }
        if (-not ($current -match ('^' + [regex]::Escape($id) + '\|'))) { continue }
        Write-Host "Switching Chocolatey package $id ($($packages[$id])) to the Node 24 LTS channel..."
        # Exact package names only. Let Chocolatey reject dependent-package conflicts.
        Invoke-SkyviewNodeChocolatey $choco @('uninstall', $id, '-y', '--no-progress')
    }
    Invoke-SkyviewNodeChocolatey $choco @('pin', 'remove', '--name=nodejs-lts')
    try {
        Invoke-SkyviewNodeChocolatey $choco @('upgrade', 'nodejs-lts', '--version', $Version, '-y', '--no-progress', '--allow-downgrade')
        $node = 'C:\Program Files\nodejs\node.exe'
        if (-not (Test-Path $node)) { throw 'The Node installer completed but the runtime was not found.' }
        $actual = & $node --version
        if ($LASTEXITCODE -ne 0 -or $actual -notmatch '^v24\.') { throw "Expected Node 24 after installation; detected $actual." }
    }
    finally {
        Invoke-SkyviewNodeChocolatey $choco @('pin', 'add', '--name=nodejs-lts')
    }
}
