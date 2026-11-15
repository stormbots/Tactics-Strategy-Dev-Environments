# Temporary Git configs only. Native Windows CI also exercises the real validator.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/GitPreferences.ps1')
$directory=Join-Path ([IO.Path]::GetTempPath()) ('sde git preferences '+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($directory)
$keys=@('GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_CONFIG_NOSYSTEM','GIT_DIR','GIT_WORK_TREE')
$saved=@{}
foreach ($key in $keys) { $saved[$key]=[Environment]::GetEnvironmentVariable($key,'Process') }
$count=0
function Assert-GitPreference($Condition,[string]$Message) {
    if (-not $Condition) { throw $Message }
    $script:count++
}
$utf8=New-Object Text.UTF8Encoding($false)
$config=Join-Path $directory 'student.gitconfig'
$system=Join-Path $directory 'system.gitconfig'
try {
    $env:GIT_CONFIG_GLOBAL=$config
    $env:GIT_CONFIG_SYSTEM=$system
    [Environment]::SetEnvironmentVariable('GIT_CONFIG_NOSYSTEM',$null,'Process')
    [Environment]::SetEnvironmentVariable('GIT_DIR',$null,'Process')
    [Environment]::SetEnvironmentVariable('GIT_WORK_TREE',$null,'Process')
    [IO.File]::WriteAllText($system,'',$utf8)
    $result=Get-SkyviewGitPreferences
    Assert-GitPreference ($result.status -eq 'passed') 'Unset preferences did not pass.'
    Assert-GitPreference (-not [IO.File]::Exists($config)) 'Read-only check created a Git config.'
    Assert-GitPreference (@($result.preferences | Where-Object status -ne 'unset').Count -eq 0) 'Missing values were invented.'
    $initial="# retained comment`n[init]`n defaultBranch = student-choice`n[fetch]`n prune = no`n[credential]`n helper = fixture-helper`n"
    [IO.File]::WriteAllText($config,$initial,$utf8)
    $result=Get-SkyviewGitPreferences
    Assert-GitPreference ($result.status -eq 'passed') 'Harmless choices failed Git.'
    Assert-GitPreference ($result.preferences[0].status -eq 'different') 'Different branch preference was lost.'
    Assert-GitPreference ($result.preferences[1].value -ceq 'false') 'Equivalent Boolean was not normalized.'
    Assert-GitPreference ($result.preferences[2].status -eq 'unset') 'Unset pull.ff was not preserved.'
    Assert-GitPreference ([IO.File]::ReadAllText($config) -ceq $initial) 'Git config bytes changed.'
    Assert-GitPreference (($result | ConvertTo-Json -Depth 5) -notmatch 'fixture-helper') 'Unrelated settings leaked into evidence.'
    $included=Join-Path $directory 'included.gitconfig'
    [IO.File]::WriteAllText($included,"[fetch]`n prune = yes`n",$utf8)
    $includePath=$included.Replace('\','/')
    [IO.File]::WriteAllText($config,"[include]`n path = $includePath`n",$utf8)
    $env:GIT_DIR=Join-Path $directory 'missing-project/.git'
    $result=Get-SkyviewGitPreferences
    Assert-GitPreference ($result.status -eq 'passed' -and $result.preferences[1].value -ceq 'true') 'Included global preference was not verified outside project context.'
    Assert-GitPreference ($env:GIT_DIR -eq (Join-Path $directory 'missing-project/.git')) 'Parent repository environment changed.'
    [Environment]::SetEnvironmentVariable('GIT_DIR',$null,'Process')
    if ($env:OS -eq 'Windows_NT' -and $env:GITHUB_ACTIONS -eq 'true') {
        $acl=Get-Acl -LiteralPath $included
        $denied=Get-Acl -LiteralPath $included
        $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
        $rule=New-Object Security.AccessControl.FileSystemAccessRule($sid,[Security.AccessControl.FileSystemRights]::ReadData,[Security.AccessControl.AccessControlType]::Deny)
        $denied.AddAccessRule($rule)
        try {
            Set-Acl -LiteralPath $included -AclObject $denied
            Assert-GitPreference ((Get-SkyviewGitPreferences).status -eq 'incomplete') 'Unreadable included file became unset/Passed.'
        } finally { Set-Acl -LiteralPath $included -AclObject $acl }
    }
    foreach ($value in @('yes','on','1','true')) {
        [IO.File]::WriteAllText($config,"[fetch]`n prune = $value`n",$utf8)
        $result=Get-SkyviewGitPreferences
        Assert-GitPreference ($result.status -eq 'passed' -and $result.preferences[1].status -eq 'matches') 'Equivalent true value failed.'
    }
    [IO.File]::WriteAllText($config,'[broken',$utf8)
    $result=Get-SkyviewGitPreferences
    Assert-GitPreference ($result.status -eq 'incomplete' -and $result.reason -eq 'configReadFailed') 'Malformed global config became Passed.'
    [IO.File]::WriteAllText($config,'',$utf8)
    [IO.File]::WriteAllText($system,'[broken',$utf8)
    Assert-GitPreference ((Get-SkyviewGitPreferences).status -eq 'incomplete') 'Malformed system config was ignored.'
    [IO.File]::WriteAllText($system,'',$utf8)
    [IO.File]::WriteAllText($config,"[fetch]`n prune = not-a-bool`n",$utf8)
    Assert-GitPreference ((Get-SkyviewGitPreferences).status -eq 'incomplete') 'Unreadable Boolean became a harmless difference.'
    $originalQuery=${function:Invoke-SkyviewGitQuery}
    try {
        function Invoke-SkyviewGitQuery { return @{Code=-1;Text=''} }
        Assert-GitPreference ((Get-SkyviewGitPreferences).status -eq 'incomplete') 'Unavailable check became Passed.'
        function Invoke-SkyviewGitQuery {
            param($Executable,$Arguments,$Directory)
            if ($Arguments -contains '--version') { return @{Code=7;Text='git version 2.43.0'} }
            return @{Code=1;Text=''}
        }
        Assert-GitPreference ((Get-SkyviewGitPreferences).status -eq 'unusable') 'Failed command supplied a version-text pass.'
    } finally { ${function:Invoke-SkyviewGitQuery}=$originalQuery }
    Write-Host "GIT_PREFERENCES_CONTRACTS_OK ($count assertions)"
} finally {
    foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key,$saved[$key],'Process') }
    [IO.Directory]::Delete($directory,$true)
}
$global:LASTEXITCODE=0
