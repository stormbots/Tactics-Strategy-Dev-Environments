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
    exit 0
}

foreach ($Repo in $Repos) {
    if (-not $Repo.Url) { continue }
    $Folder = if ($Repo.Folder) { $Repo.Folder } elseif ($Repo.Name) { $Repo.Name } else { [IO.Path]::GetFileNameWithoutExtension($Repo.Url) }
    $Destination = Join-Path $Root $Folder

    if (Test-Path (Join-Path $Destination '.git')) {
        Write-Host "$($Repo.Name): already cloned at $Destination"
        continue
    }

    Write-Host "Cloning $($Repo.Name) -> $Destination"
    git clone $Repo.Url $Destination
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Clone failed for $($Repo.Name). Authentication may be required; GitHub authentication policy is intentionally not configured by this package."
    }
}
