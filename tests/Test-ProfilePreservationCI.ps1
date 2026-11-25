# Disposable native CI only; real profile script, real non-admin account/files.
# Controlled empty extension/repository inputs avoid external downloads. This is
# the shared Install/Repair PROFILE phase, not another full package installation.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub runner required.' }
$coordination = 'C:\ProgramData\SkyviewRoboticsCoordination'
if (Test-Path (Join-Path $coordination 'transaction.json')) { throw 'Unexpected retained transaction; do not clear it.' }
if (@(Import-Csv 'C:\ProgramData\SkyviewRobotics\repositories.csv').Count -ne 0) { throw 'Expected empty disposable repository policy.' }
$backend = Join-Path $PSScriptRoot '../windows/chocolatey/tools'
$fixture = Join-Path 'C:\Users\Public' ('SdeProfileProbe-' + [guid]::NewGuid().ToString('N'))
$user = 'SdeProfile' + [guid]::NewGuid().ToString('N').Substring(0,6)
$created = $false
New-Item -ItemType Directory $fixture | Out-Null
try {
    foreach ($name in @('Configure-SkyviewUser.ps1','EditorExtensions.ps1','EditorLocation.ps1','ProjectLocation.ps1','Coordination.ps1','Setup-SkyviewRepositories.ps1','settings.json')) {
        Copy-Item (Join-Path $backend $name) $fixture
        if ((Get-FileHash (Join-Path $fixture $name)).Hash -cne (Get-FileHash (Join-Path $backend $name)).Hash) { throw 'Profile code copy changed.' }
    }
    & git.exe init -q (Join-Path $fixture 'foreign repository')
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare foreign-owned Git fixture.' }
    '# Controlled empty extension fixture' | Set-Content (Join-Path $fixture 'extensions.txt') -Encoding UTF8
    $probe = Join-Path $fixture 'student.ps1'
    @'
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Expected actual standard user.' }
$env:HOME = $env:USERPROFILE
Remove-Item Env:GIT_CONFIG_GLOBAL -ErrorAction SilentlyContinue
Remove-Item Env:GIT_CONFIG_SYSTEM -ErrorAction SilentlyContinue
$env:GIT_CONFIG_NOSYSTEM = '1'
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
& git config --global user.name 'Synthetic Student'
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare fixture Git identity.' }
& git config --global user.email 'student@example.invalid'
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare fixture Git identity.' }
& git config --global init.defaultBranch student-choice
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare fixture Git preference.' }
& git config --global fetch.prune no
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare fixture Git Boolean.' }
# Leave pull.ff unset and require it to remain unset through both profile runs.
$gitConfig = Join-Path $env:USERPROFILE '.gitconfig'
$beforeGit = (Get-FileHash $gitConfig).Hash
$project = Join-Path 'C:\Development' ('SdeProfile-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $project | Out-Null
$sentinel = Join-Path $project 'student-project.txt'
$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($sentinel,'synthetic student project bytes',$utf8)
$beforeProject = (Get-FileHash $sentinel).Hash
$settings = Join-Path $env:APPDATA 'VSCodium\User\settings.json'
New-Item -ItemType Directory (Split-Path $settings) -Force | Out-Null
[IO.File]::WriteAllText($settings,"// student JSONC`n{`"editor.fontSize`":19,`"sde.fixture`":`"keep`"}`n",$utf8)
$beforeSettings = (Get-FileHash $settings).Hash
for ($attempt = 0; $attempt -lt 2; $attempt++) {
    & 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Configure-SkyviewUser.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Real standard-user profile phase failed.' }
    if ((Get-FileHash $sentinel).Hash -cne $beforeProject) { throw 'Existing student project changed.' }
    if ((Get-FileHash $settings).Hash -cne $beforeSettings) { throw 'Existing editor settings changed.' }
    if ((Get-FileHash $gitConfig).Hash -cne $beforeGit) { throw 'Existing Git configuration bytes changed.' }
    if (Test-Path 'C:\ProgramData\SkyviewRoboticsCoordination\transaction.json') { throw 'Unexpected system transaction after profile setup.' }
}
foreach ($missing in @($false,$true)) {
    if ($missing) { Remove-Item -LiteralPath $settings }
    else { [IO.File]::WriteAllText($settings,'',$utf8) }
    & 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Configure-SkyviewUser.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Profile phase failed for default preferences.' }
    if ($missing) { if (Test-Path -LiteralPath $settings) { throw 'Missing preferences were silently created.' } }
    elseif ((Get-Item -LiteralPath $settings).Length -ne 0) { throw 'Empty preferences were replaced.' }
    if ((Get-FileHash $gitConfig).Hash -cne $beforeGit -or (Get-FileHash $sentinel).Hash -cne $beforeProject) { throw 'Project/Git changed while preserving default preferences.' }
    if (Test-Path 'C:\ProgramData\SkyviewRoboticsCoordination\transaction.json') { throw 'Unexpected system transaction after profile setup.' }
}
foreach ($check in @(@('user.name','Synthetic Student'),@('user.email','student@example.invalid'),@('init.defaultBranch','student-choice'),@('fetch.prune','no'))) {
    $actual = & git config --global $check[0]
    if ($LASTEXITCODE -ne 0 -or $actual -cne $check[1]) { throw 'Identity or Git preference preservation failed.' }
}
& git config --global --get pull.ff
if ($LASTEXITCODE -ne 1) { throw 'An unset Git preference was changed.' }
if ((Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced').HideFileExt -ne 0) { throw 'Disclosed Explorer configuration not applied.' }
. (Join-Path $PSScriptRoot 'ProjectLocation.ps1')
$source=Join-Path $env:USERPROFILE 'worktree source'
$linked=Join-Path $env:USERPROFILE 'linked worktree'
& git.exe init -q $source
if ($LASTEXITCODE -ne 0) { throw 'Could not initialize student repository.' }
& git.exe -C $source -c commit.gpgsign=false commit -qm fixture --allow-empty
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare student repository commit.' }
& git.exe -C $source worktree add -qb student-worktree $linked
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare student worktree.' }
$dirty=Join-Path $linked 'uncommitted.txt'
[IO.File]::WriteAllText($dirty,'keep student work',$utf8)
$dirtyHash=(Get-FileHash $dirty).Hash
$localConfig=(Get-FileHash (Join-Path $source '.git/config')).Hash
if ((Get-SkyviewProjectLocation $source).status -cne 'verified') { throw 'Real standard-user repository did not verify.' }
if ((Get-SkyviewProjectLocation $linked).status -cne 'verified') { throw 'Real standard-user worktree did not verify.' }
if ((Get-SkyviewProjectLocation (Join-Path $PSScriptRoot 'foreign repository')).status -cne 'incomplete') { throw 'Git ownership trust refusal was bypassed.' }
if ((Get-FileHash $dirty).Hash -cne $dirtyHash -or (Get-FileHash (Join-Path $source '.git/config')).Hash -cne $localConfig -or (Get-FileHash $gitConfig).Hash -cne $beforeGit) { throw 'Read-only project inspection changed student files/configuration.' }
Write-Output 'SDE_PROJECT_WORKTREE_STANDARD_USER_WINDOWS_OK'
Write-Output 'SDE_PROFILE_PRESERVATION_WINDOWS_OK'
exit 0
'@ | Set-Content $probe -Encoding UTF8
    $password = ConvertTo-SecureString ('Ci!' + [guid]::NewGuid().ToString('N') + 'aA7') -AsPlainText -Force
    $credential = New-Object Management.Automation.PSCredential("$env:COMPUTERNAME\$user",$password)
    New-LocalUser -Name $user -Password $password -AccountNeverExpires -PasswordNeverExpires | Out-Null
    $created = $true
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user
    Start-Service seclogon
    $stdout = Join-Path $fixture 'stdout.txt'; $stderr = Join-Path $fixture 'stderr.txt'
    $process = Start-Process 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$probe`"" -Credential $credential -LoadUserProfile -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    [void]$process.Handle
    $process.WaitForExit()
    if ($process.ExitCode -ne 0 -or -not (Select-String $stdout -Pattern '^SDE_PROFILE_PRESERVATION_WINDOWS_OK\s*$')) {
        # Synthetic output only; never credential/environment/profile dumps.
        Get-Content $stdout,$stderr | Write-Output
        throw 'Profile preservation fixture failed.'
    }
    $process.Dispose()
    Write-Output 'SDE_PROFILE_PRESERVATION_WINDOWS_OK'
} finally {
    if ($created) { Remove-LocalUser $user }
    # Keep synthetic files on failure for diagnosis; never delete journals/locks.
}
$global:LASTEXITCODE = 0
