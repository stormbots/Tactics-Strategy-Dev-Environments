$ErrorActionPreference = 'Stop'
$helper = Join-Path $PSScriptRoot '../windows/chocolatey/tools/PythonRuntime.ps1'
. $helper
# Exercise the actual process/argument/deadline adapter before using fixtures.
$hostExe = (Get-Process -Id $PID).Path
$query = Invoke-SkyviewPythonQuery $hostExe @('-NoLogo','-NoProfile','-NonInteractive','-Command','[Console]::Write("path with spaces and quotes: " + [char]34 + "ok" + [char]34)') 5000
if ($query.Code -ne 0 -or $query.Text -ne 'path with spaces and quotes: "ok"') { throw 'Read-only query quoting/output failed.' }
$query = Invoke-SkyviewPythonQuery $hostExe @('-NoLogo','-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 10') 100
if ($query.Reason -ne 'timeout') { throw 'Read-only query did not enforce its deadline.' }
$query = Invoke-SkyviewPythonQuery $hostExe @('-NoLogo','-NoProfile','-NonInteractive','-Command','exit 7') 5000
if ($query.Code -ne 7) { throw 'Read-only query lost the exit code.' }

$originalGetCommand = ${function:Get-Command}
$beforePath = $env:PATH
$beforePythonPath = $env:PYTHONPATH
$script:checks = 0
function Assert($Condition,[string]$Message) { if (-not $Condition) { throw $Message }; $script:checks++ }
function Reset-Case {
    $script:paths = @('C:\Python315\python.exe')
    $script:requiredPaths = @()
    $script:complete = $true
    $script:launcher = $true
    $script:launcherText = " -V:3.15 * C:\Python315\python.exe`n -V:3.14 C:\Python 314\python.exe"
    $script:queries = New-Object 'System.Collections.Generic.List[object]'
    $script:versions = @{'C:\Python315\python.exe'='3.15.1'; 'C:\Python 314\python.exe'='3.14.9'}
    $script:failed = @{}
    $script:malformed = @{}
    $script:pip = 'pip 25.3 from C:\Python 314\Lib\site-packages\pip (python 3.14)'
    $script:pipCode = 0
    $script:pipReason = 'completed'
}
function Get-Command {
    param([string]$Name, $CommandType, $ErrorAction)
    if ($Name -eq 'py.exe' -and $script:launcher) { return [pscustomobject]@{Source='C:\Windows\py.exe'} }
}
function Get-SkyviewPythonCandidates {
    return [pscustomobject]@{Paths=$script:paths; RequiredPaths=$script:requiredPaths; Complete=$script:complete}
}
function Test-SkyviewPythonExecutable([string]$Path) { return $script:versions.ContainsKey($Path) }
function Invoke-SkyviewPythonQuery {
    param([string]$Executable,[string[]]$Arguments,[int]$TimeoutMs)
    Assert ($TimeoutMs -gt 0 -and $TimeoutMs -le 2500) 'Probe lost its bounded deadline.'
    $script:queries.Add([pscustomobject]@{Executable=$Executable; Arguments=$Arguments})
    if ($script:failed.ContainsKey($Executable)) { return @{Code=1;Text='';Reason=$script:failed[$Executable]} }
    if ($Executable -eq 'C:\Windows\py.exe') {
        Assert ($Arguments.Count -eq 1 -and $Arguments[0] -eq '-0p') 'Discovery requested interpreter execution or installation through the launcher.'
        return @{Code=0;Text=$script:launcherText;Reason='completed'}
    }
    Assert ($Arguments -contains '-B') 'Python probe may write bytecode.'
    Assert ($Arguments -contains '-I') 'Python probe is not isolated from project/environment imports.'
    if ($Arguments -contains 'pip') { return @{Code=$script:pipCode; Text=$script:pip; Reason=$script:pipReason} }
    if ($script:malformed.ContainsKey($Executable)) { return @{Code=0;Text='not JSON';Reason='completed'} }
    return @{Code=0;Text=(@{version=$script:versions[$Executable];executable=$Executable}|ConvertTo-Json -Compress);Reason='completed'}
}
try {
    Reset-Case
    $result = Get-SkyviewPythonRuntime
    Assert ($result.status -eq 'passed' -and $result.version -eq '3.14.9') 'Newer default rejected usable 3.14.'
    Assert ($result.executable -eq 'C:\Python 314\python.exe' -and $result.pipVersion -eq '25.3') 'Selected evidence is wrong.'
    Assert (@($script:queries | Where-Object {$_.Arguments -contains 'pip' -and $_.Executable -ne $result.executable}).Count -eq 0) 'pip used another Python.'
    Assert (@($script:queries | Where-Object {$_.Executable -eq 'C:\Python315\python.exe'}).Count -eq 0) 'Unrelated default was unnecessarily probed.'

    Reset-Case; $script:launcher=$false; $script:paths=@('C:\Python315\python.exe','C:\Python 314\python.exe'); $script:requiredPaths=@('C:\Python 314\python.exe')
    Assert ((Get-SkyviewPythonRuntime).status -eq 'passed') 'Registered side-by-side Python failed without launcher.'
    $script:versions['C:\Python315\python.exe']='3.13.7'
    Assert ((Get-SkyviewPythonRuntime).status -eq 'passed') 'Older default rejected usable 3.14.'

    Reset-Case; $script:launcher=$false
    Assert ((Get-SkyviewPythonRuntime).status -eq 'notFound') 'Completed search of another family was not distinguished.'
    $script:complete=$false
    Assert ((Get-SkyviewPythonRuntime).status -eq 'incomplete') 'Unreadable registration was called absence.'

    Reset-Case; $script:complete=$false
    Assert ((Get-SkyviewPythonRuntime).status -eq 'passed') 'An unrelated unreadable source rejected a verified installation.'
    Reset-Case; $script:launcherText=' -3.14-64 C:\Python 314\python.exe'
    Assert ((Get-SkyviewPythonRuntime).status -eq 'passed') 'Legacy launcher registration format was lost.'
    Reset-Case; $script:launcherText='Diagnostic: run C:\Python 314\python.exe'
    Assert ((Get-SkyviewPythonRuntime).status -eq 'incomplete') 'Arbitrary diagnostics supplied an executable candidate.'
    Reset-Case; $script:failed['C:\Windows\py.exe']='unavailable'
    Assert ((Get-SkyviewPythonRuntime).status -eq 'incomplete') 'Failed launcher was called absence.'
    Reset-Case; $script:malformed['C:\Python 314\python.exe']=$true
    Assert ((Get-SkyviewPythonRuntime).status -eq 'incomplete') 'Malformed discovery output was accepted.'

    Reset-Case; $script:pipCode=1
    $result=Get-SkyviewPythonRuntime
    Assert ($result.status -eq 'unusable' -and $result.reason -eq 'pipFailed') 'Broken pip was accepted.'
    Reset-Case; $script:pip='pip 25.3 from another installation (python 3.15)'
    Assert ((Get-SkyviewPythonRuntime).status -eq 'unusable') 'Another Python pip supplied a pass.'
    Reset-Case; $script:pipCode=-1; $script:pipReason='timeout'
    $result=Get-SkyviewPythonRuntime
    Assert ($result.status -eq 'incomplete' -and $result.reason -eq 'pipTimeout') 'Timeout was called missing or verified.'

    Reset-Case; $script:launcher=$false; $script:paths=@('C:\Python 314\python.exe'); $script:requiredPaths=$script:paths; $script:failed[$script:paths[0]]='unavailable'
    Assert ((Get-SkyviewPythonRuntime).status -eq 'unusable') 'Registered but unusable Python was called missing.'
    Assert ($env:PATH -ceq $beforePath -and $env:PYTHONPATH -ceq $beforePythonPath) 'Validation changed the environment.'
} finally {
    # Restore production definitions before the native smoke, including Get-Command.
    if ($originalGetCommand) { ${function:Get-Command}=$originalGetCommand } else { Remove-Item Function:Get-Command }
    . $helper
}
# On Windows this exercises actual registration, launcher and selected interpreter
# queries. Presence on a runner is not a complete coexistence/device fixture.
if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
    $live=Get-SkyviewPythonRuntime
    Assert ($live.status -in @('passed','notFound','unusable','incomplete')) 'Live runtime result has no valid state.'
    if ($live.status -eq 'passed') {
        Assert ($live.version -match '^3\.14\.' -and $live.pipVersion -and (Test-SkyviewPythonExecutable $live.executable)) 'Live Python pass lacks complete evidence.'
    }
    Write-Host "WINDOWS_PYTHON_RUNTIME_NATIVE_OBSERVED $($live.status)"
}
Write-Host "PYTHON_RUNTIME_CONTRACTS_OK ($script:checks assertions)"
