param(
    [string]$Config = 'C:\ProgramData\SkyviewRobotics\repositories.csv',
    [string]$Root = 'C:\Development'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Config)) { throw "Repository configuration not found: $Config" }
New-Item -ItemType Directory -Path $Root -Force | Out-Null

$Repos = Import-Csv $Config
if (-not $Repos) {
    Write-Host 'No repositories are configured yet.'
    Write-Host "Edit $Config and add rows with Name,Url,Folder."
    return
}

foreach ($Repo in $Repos) {
    if (-not $Repo.Url) { continue }
    $Folder = if ($Repo.Folder) { $Repo.Folder } elseif ($Repo.Name) { $Repo.Name } else { [IO.Path]::GetFileNameWithoutExtension($Repo.Url) }
    if ($Folder -notmatch '^[a-zA-Z0-9_-][a-zA-Z0-9._-]*$' -or $Folder -eq '..') { throw "Invalid repository folder: $Folder" }
    if ($Repo.Url -notmatch '^(https://|git@)') { throw 'Unsupported repository URL.' }
    $Destination = Join-Path $Root $Folder
    if ((Test-Path $Destination) -and -not (Test-Path (Join-Path $Destination '.git'))) {
        Write-Warning "Existing folder preserved: $Destination"
        continue
    }

    if (Test-Path (Join-Path $Destination '.git')) {
        Write-Host "$($Repo.Name): already cloned at $Destination"
        continue
    }

    Write-Host "Cloning $($Repo.Name) -> $Destination"
    $env:GIT_TERMINAL_PROMPT = '0'
    git clone -- $Repo.Url $Destination
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Clone failed for $($Repo.Name). Authentication may be required; GitHub authentication policy is intentionally not configured by this package."
    }
}
