param([switch]$CheckUpdates)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Coordination.ps1')
try {
Invoke-SkyviewCoordinated -ReadOnly -Action {
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$ErrorActionPreference = 'Continue'
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$script:Failures = 0
$installed = @{}
function Result($Status,$Message) {
    if ($Status -eq 'FAIL') { $script:Failures++ }
    Write-Host ("SKYVIEW_EVENT|validation|{0}|{1}" -f $Status,($Message -replace '[\r\n]',' '))
    Write-Host "$Status $Message"
}
function Check($Condition,$Message) { if ($Condition) { Result PASS $Message } else { Result FAIL $Message } }
foreach ($check in @(
    @{Name='GitHub CLI'; Command='gh'; Args=@('--version')},
    @{Name='VSCodium'; Command='codium'; Args=@('--version')},
    @{Name='PowerShell 7'; Command='pwsh'; Args=@('--version')},
    @{Name='OpenSSH'; Command='ssh'; Args=@('-V')},
    @{Name='7-Zip'; Command='7z'; Args=@('i')}
)) {
    $cmd = Get-Command $check.Command -ErrorAction SilentlyContinue
    if (-not $cmd) { Result FAIL "$($check.Name): not installed"; continue }
    $out = @(& $cmd.Source @($check.Args) 2>&1)
    $code = $LASTEXITCODE
    $version = [string]($out | Where-Object { [string]$_ -notmatch '^\s*$' } | Select-Object -First 1)
    if ($check.Name -eq 'VSCodium') {
        $version=[string]($out | Where-Object { [string]$_ -match '^\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.+-]+)?$' } | Select-Object -First 1)
        if ($code -ne 0 -or -not $version) { Result FAIL 'VSCodium: SDE could not finish checking the editor command.';continue }
    }
    if ($code -eq 0 -and $version -match '\d+(?:\.\d+)+(?:[^\s]*)?') { $installed[$check.Name] = $Matches[0] }
    if ($code -ne 0 -or ($check.Family -and $version -notmatch $check.Family)) {
        Result FAIL "$($check.Name): expected runtime family or usable command; detected $version"
    } else { Result PASS "$($check.Name): $version" }
}
. (Join-Path $PSScriptRoot 'NodeRuntime.ps1')
$nodeRuntime=Get-SkyviewNodeRuntime
Write-Host ("SKYVIEW_EVENT|runtime|Node.js|{0}" -f ($nodeRuntime | ConvertTo-Json -Compress))
switch ($nodeRuntime.status) {
    'passed' {
        $installed['Node.js']=$nodeRuntime.version
        $installed['npm']=$nodeRuntime.npmVersion
        Result PASS "Node.js: $($nodeRuntime.version); its npm $($nodeRuntime.npmVersion) verified with the same Node"
    }
    'notFound' { Result FAIL 'Node.js: the supported search did not find Node 24. Other versions can stay installed.' }
    'unusable' { Result FAIL 'Node.js: Node 24 or its npm check did not work. Review the check details.' }
    default { Result FAIL 'Node.js: SDE could not finish checking Node 24 and npm. This does not mean they are missing.' }
}
. (Join-Path $PSScriptRoot 'PythonRuntime.ps1')
$pythonRuntime = Get-SkyviewPythonRuntime
Write-Host ("SKYVIEW_EVENT|runtime|Python|{0}" -f ($pythonRuntime | ConvertTo-Json -Compress))
switch ($pythonRuntime.status) {
    'passed' {
        $installed['Python'] = $pythonRuntime.version
        Result PASS "Python: $($pythonRuntime.version); pip $($pythonRuntime.pipVersion) verified with the same Python"
    }
    'notFound' { Result FAIL 'Python: the supported search did not find Python 3.14. Other versions can stay installed.' }
    'unusable' { Result FAIL 'Python: Python 3.14 or its pip check did not work. Review the check details.' }
    default { Result FAIL 'Python: SDE could not finish checking Python 3.14. This does not mean it is missing.' }
}
foreach ($entry in @(
    @{Name='DBeaver'; Paths=@('C:\Program Files\DBeaver\dbeaver.exe','C:\Program Files\DBeaver\dbeaver-ce.exe')},
    @{Name='PyCharm'; Paths=@('C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe')},
    @{Name='Chrome'; Paths=@('C:\Program Files\Google\Chrome\Application\chrome.exe','C:\Program Files (x86)\Google\Chrome\Application\chrome.exe')},
    @{Name='Firefox'; Paths=@('C:\Program Files\Mozilla Firefox\firefox.exe','C:\Program Files (x86)\Mozilla Firefox\firefox.exe')}
)) {
    $found = @($entry.Paths | ForEach-Object { Get-Item $_ -ErrorAction SilentlyContinue } | Select-Object -First 1)
    if ($found.Count) {
        $productVersion = $found[0].VersionInfo.ProductVersion
        if ($productVersion -match '\d+(?:\.\d+)+(?:[^\s]*)?') { $installed[$entry.Name] = $Matches[0] }
        if ($entry.Name -eq 'PyCharm') {
            $productInfo = Join-Path (Split-Path (Split-Path $found[0].FullName -Parent) -Parent) 'product-info.json'
            if (Test-Path $productInfo) {
                try { $installed.PyCharm = (Get-Content $productInfo -Raw | ConvertFrom-Json).version } catch { Write-Verbose 'PyCharm version metadata unavailable.' }
            }
        }
        Result PASS "$($entry.Name): $productVersion"
    }
    else { Result FAIL "$($entry.Name): not installed" }
}
Check (Test-Path 'C:\Development') 'Development folder'
. (Join-Path $PSScriptRoot 'GitPreferences.ps1')
$gitPreferences=Get-SkyviewGitPreferences
Write-Host ("SKYVIEW_EVENT|preferences|Git|{0}" -f ($gitPreferences | ConvertTo-Json -Compress -Depth 5))
switch ($gitPreferences.status) {
    'passed' {
        $installed['Git']=$gitPreferences.version
        Result PASS 'Git: Git is available. Your existing preferences were preserved.'
    }
    'notFound' { Result FAIL 'Git: SDE could not find Git.' }
    'unusable' { Result FAIL 'Git: the Git command did not work. Review the check details.' }
    default {
        if ($gitPreferences.reason -eq 'configReadFailed') { Result FAIL 'Git: SDE could not finish reading your Git settings. Review the check details.' }
        else { Result FAIL 'Git: SDE could not finish checking Git. Review the check details.' }
    }
}
Result INFO 'Git identity and GitHub sign-in are optional.'
if ($CheckUpdates -and (Get-Command gh -ErrorAction SilentlyContinue)) {
    & gh auth status *> $null
    if ($LASTEXITCODE -eq 0) { Result INFO 'GitHub authentication: configured locally' }
    else { Result INFO 'GitHub authentication: not configured (optional)' }
}
. (Join-Path $PSScriptRoot 'ScheduledMaintenance.ps1')
$maintenance = Get-SkyviewMaintenanceResult
Result $maintenance.Status $maintenance.Message
$longPaths = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
Check ($longPaths -eq 1) 'Windows long paths enabled'
$devMode = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock' -Name AllowDevelopmentWithoutDevLicense -ErrorAction SilentlyContinue).AllowDevelopmentWithoutDevLicense
Check ($devMode -eq 1) 'Windows developer mode enabled'
$fileExt = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced' -Name HideFileExt -ErrorAction SilentlyContinue).HideFileExt
Check ($fileExt -eq 0) 'File extensions visible'
. (Join-Path $PSScriptRoot 'EditorPreferences.ps1')
$editorPreferences=Get-SkyviewEditorPreferences -NodeObservation $nodeRuntime
Write-Host ("SKYVIEW_EVENT|preferences|VSCodium|{0}" -f ($editorPreferences | ConvertTo-Json -Compress -Depth 5))
switch ($editorPreferences.status) {
    'read' { Result INFO 'VSCodium preferences were read. Your choices were preserved; they may differ from the suggestions.' }
    'missing' { Result INFO 'VSCodium has no user preferences file here. It can use its defaults.' }
    'invalid' { Result WARNING 'SDE could open your VSCodium preferences file, but could not understand its contents. Your settings have not been changed.' }
    'unreadable' {
        if ($editorPreferences.reason -eq 'accessDenied') { Result WARNING 'SDE could not open the file that stores your VSCodium preferences because it did not have permission to read it. Your settings have not been changed, and VSCodium may still work normally.' }
        else { Result WARNING 'SDE could not read your VSCodium preferences file. Your settings have not been changed; the cause is not yet known.' }
    }
    default { Result WARNING 'SDE could not finish checking your VSCodium preferences. Your settings have not been changed. This does not mean they are missing or damaged.' }
}
if (Get-Command codium -ErrorAction SilentlyContinue) {
    $extensions = @(& codium --list-extensions 2>$null)
    $extensionsExit=$LASTEXITCODE
    if ($extensionsExit -ne 0) { Result FAIL 'VSCodium: SDE could not finish checking the installed extensions.' }
    else {
    try { $requiredExtensions=@(Get-Content (Join-Path $PSScriptRoot 'extensions.txt') -ErrorAction Stop | Where-Object { $_ -and $_ -notmatch '^\s*#' }) }
    catch { Result FAIL 'VSCodium: SDE could not read the list of required extensions.';$requiredExtensions=@() }
    foreach ($ext in $requiredExtensions) {
        Check ($extensions -contains $ext) "Editor extension: $ext"
    }
    }
}
$config = 'C:\ProgramData\SkyviewRobotics\repositories.csv'
if (Test-Path $config) {
    foreach ($repo in (Import-Csv $config)) {
        if (-not $repo.Url) { continue }
        $folder = if ($repo.Folder) { $repo.Folder } else { $repo.Name }
        Check (Test-Path (Join-Path "C:\Development\$folder" '.git')) "Configured repository: $($repo.Name)"
    }
}
. (Join-Path $PSScriptRoot 'ToolRecords.ps1')
foreach ($record in (Get-SkyviewToolRecords -Installed $installed -CheckUpdates ([bool]$CheckUpdates))) {
    Write-Host ("SKYVIEW_EVENT|tool|{0}|{1}" -f $record.tool, ($record | ConvertTo-Json -Compress))
    if ($record.updateAvailable) { Write-Host "SKYVIEW_EVENT|update|available|$($record.tool): $($record.installedVersion) to $($record.availableVersion)" }
}
Write-Host "SKYVIEW_EVENT|summary|$script:Failures|Validation completed with $script:Failures failed checks"
if ($script:Failures -gt 0) { exit 1 }
exit 0

}
} catch {
    if ($_.Exception.Message -eq 'SKYVIEW_DEFERRED') {
        Write-Host 'SKYVIEW_EVENT|warning|deferred|SDE is busy. Maintenance will retry at its next scheduled invocation.'
        exit 75
    }
    throw
}
