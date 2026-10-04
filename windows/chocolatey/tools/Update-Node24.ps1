param(
    [string]$Version
)

$ErrorActionPreference = 'Stop'
$Chocolatey = 'C:\ProgramData\chocolatey\bin\choco.exe'
if (-not (Test-Path $Chocolatey)) { throw 'Chocolatey executable not found.' }

if (-not $Version) {
    Write-Host 'Finding the newest Node.js 24.x package available from Chocolatey...'
    $rows = & $Chocolatey search nodejs-lts --exact --all-versions --limit-output
    $versions = foreach ($row in $rows) {
        if ($row -match '^nodejs-lts\|(.+)$') {
            $candidate = $Matches[1]
            try {
                $v = [version]$candidate
                if ($v.Major -eq 24) { $v }
            } catch { }
        }
    }
    $target = $versions | Sort-Object -Descending | Select-Object -First 1
    if (-not $target) { throw 'No Node.js 24.x nodejs-lts package was found.' }
    $Version = $target.ToString()
}

$parsed = [version]$Version
if ($parsed.Major -ne 24) {
    throw "Refusing Node.js $Version. This workstation baseline is pinned to Node.js major 24."
}

Write-Host "Updating approved Node.js runtime to $Version..."
& $Chocolatey pin remove --name=nodejs-lts | Out-Null
try {
    & $Chocolatey upgrade nodejs-lts --version $Version -y --no-progress --allow-downgrade
    if ($LASTEXITCODE -notin @(0, 1605, 1614, 1641, 3010)) {
        throw "Node.js update failed with exit code $LASTEXITCODE"
    }
}
finally {
    & $Chocolatey pin add --name=nodejs-lts | Out-Null
}

Write-Host "Node.js $Version installed and nodejs-lts re-pinned."
