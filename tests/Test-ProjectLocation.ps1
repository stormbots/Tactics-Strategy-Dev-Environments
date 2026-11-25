$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/ProjectLocation.ps1')
function Assert-Project($condition,$message) { if (-not $condition) { throw $message } }
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('sde project '+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $fixture | Out-Null
$projectEnvironment=@{}
$initialProjectEnvironment=[Environment]::GetEnvironmentVariables()
foreach ($key in @($initialProjectEnvironment.Keys | Where-Object { $_ -like 'GIT_*' })) { $projectEnvironment[$key]=[string]$initialProjectEnvironment[$key] }
try {
    foreach ($key in $projectEnvironment.Keys) { Remove-Item -LiteralPath ("Env:"+$key) -ErrorAction Stop }
    $env:GIT_CONFIG_NOSYSTEM='1'
    $env:GIT_CONFIG_GLOBAL=Join-Path $fixture 'controlled-global.gitconfig'
    [IO.File]::WriteAllText($env:GIT_CONFIG_GLOBAL,'')
    if (-not $fixture -or (Test-Path -LiteralPath 'Env:GIT_DIR')) { throw 'Project fixture environment was not isolated.' }
    function Test-SkyviewEditorOrdinaryUser { return $false }
    Assert-Project ((Get-SkyviewProjectLocation $fixture).reason -ceq 'normalUserRequired') 'Elevated project inspection was allowed.'
    function Test-SkyviewEditorOrdinaryUser { return $true }
    & git.exe init -q $fixture
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare owned Git fixture.' }
    & git.exe -C $fixture -c user.name='Synthetic Student' -c user.email=student@example.invalid -c commit.gpgsign=false commit -qm fixture --allow-empty
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare fixture commit.' }
    $configHash=(Get-FileHash (Join-Path $fixture '.git/config')).Hash
    Assert-Project ((Get-SkyviewProjectLocation $fixture).status -ceq 'verified') 'Real Git root not verified.'
    $worktree=Join-Path $fixture 'linked worktree'
    & git.exe -C $fixture worktree add -qb student-worktree $worktree
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare linked worktree.' }
    Assert-Project (-not (Get-Item -LiteralPath (Join-Path $worktree '.git')).PSIsContainer) 'Worktree fixture lacks Git file.'
    Assert-Project ((Get-SkyviewProjectLocation $worktree).status -ceq 'verified') 'Linked worktree not verified.'
    $child=Join-Path $fixture 'ordinary child';New-Item -ItemType Directory $child | Out-Null
    Assert-Project ((Get-SkyviewProjectLocation $child).reason -ceq 'rootMismatch') 'Parent Git repository certified a child.'
    $fake=Join-Path $fixture 'fake';New-Item -ItemType Directory $fake | Out-Null
    [IO.File]::WriteAllText((Join-Path $fake '.git'),'gitdir: C:\missing-sde-project-fixture')
    Assert-Project ((Get-SkyviewProjectLocation $fake).status -ceq 'incomplete') 'Broken Git file certified a project.'
    Assert-Project ((Get-FileHash (Join-Path $fixture '.git/config')).Hash -ceq $configHash) 'Project Git config changed.'
    foreach ($path in @('relative',($fixture+'|unsafe'),($fixture+"`n"))) {
        Assert-Project ((Get-SkyviewProjectLocation $path).reason -ceq 'unsupportedPath') 'Unsafe project path accepted.'
    }
    $savedDir=$env:GIT_DIR;$savedTrace=$env:GIT_TRACE
    try {
        $env:GIT_DIR=Join-Path $fixture '.git';$env:GIT_TRACE=Join-Path $fixture 'trace'
        Assert-Project ((Get-SkyviewProjectLocation $child).status -ceq 'incomplete') 'Ambient GIT_DIR certified another folder.'
        Assert-Project ((Get-SkyviewProjectLocation $fixture).status -ceq 'verified') 'Owned repository check failed with ambient environment.'
        Assert-Project (-not (Test-Path -LiteralPath $env:GIT_TRACE)) 'Read-only query wrote Git trace.'
        Assert-Project ($env:GIT_DIR -ceq (Join-Path $fixture '.git')) 'Parent environment changed.'
    } finally { $env:GIT_DIR=$savedDir;$env:GIT_TRACE=$savedTrace }
    function Invoke-SkyviewEditorQuery { return @{Code=-1;Text=''} }
    Assert-Project ((Get-SkyviewProjectLocation $fixture).status -ceq 'incomplete') 'Failed query became a pass.'
    function Invoke-SkyviewEditorQuery { return @{Code=0;Text='malformed'} }
    Assert-Project ((Get-SkyviewProjectLocation $fixture).status -ceq 'incomplete') 'Malformed query became a pass.'
    function Get-Command { return $null }
    Assert-Project ((Get-SkyviewProjectLocation $fixture).reason -ceq 'gitUnavailable') 'Missing Git became a missing project or a pass.'
    $global:LASTEXITCODE=0
    Write-Host 'SDE_PROJECT_WORKING_FOLDER_WINDOWS_OK'
} finally {
    foreach ($key in @([Environment]::GetEnvironmentVariables().Keys | Where-Object { $_ -like 'GIT_*' })) { Remove-Item -LiteralPath ("Env:"+$key) -ErrorAction SilentlyContinue }
    foreach ($key in $projectEnvironment.Keys) { [Environment]::SetEnvironmentVariable($key,$projectEnvironment[$key],'Process') }
    Remove-Item -LiteralPath $fixture -Recurse -Force
}
