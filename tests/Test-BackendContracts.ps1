$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Get-ChildItem (Join-Path $root 'windows') -Recurse -Filter *.ps1 | ForEach-Object {
    $tokens = $null; $parseErrors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors) { throw "PowerShell parse failed: $($_.FullName): $parseErrors" }
}
# Execute only the read-only validator on the CI host, never provisioning.
# Exercise the packaged entry point, not only the validator it delegates to.
# A path containing spaces catches argument quoting and relative lookup errors.
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('Skyview validator test ' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $fixture | Out-Null
Copy-Item (Join-Path $root 'windows/chocolatey/tools/*.ps1') $fixture
Copy-Item (Join-Path $root 'windows/chocolatey/tools/extensions.txt') $fixture
Copy-Item (Join-Path $root 'windows/chocolatey/tools/NodeRuntimeProbe.cjs') $fixture
Copy-Item (Join-Path $root 'windows/chocolatey/tools/EditorSettingsProbe.cjs') $fixture
Copy-Item (Join-Path $root 'windows/chocolatey/tools/EditorIdentityProbe.cjs') $fixture
Copy-Item (Join-Path $root 'windows/chocolatey/tools/jsonc-parser') $fixture -Recurse
$validator = Join-Path $fixture 'Test-SkyviewStudentDev.ps1'
$lines = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $validator 2>&1
$code = $LASTEXITCODE
if (-not ($lines -match '^SKYVIEW_EVENT\|summary\|[0-9]+\|')) { throw 'Validator did not emit a structured summary.' }
$failed = @($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|validation\|FAIL\|' })
if ($failed.Count -gt 0 -and $code -eq 0) { throw 'Validator incorrectly returned success despite failures.' }
if ($lines -match '^SKYVIEW_EVENT\|validation\|FAIL\|Git (identity|Hub authentication)') { throw 'Optional identity became a failure.' }
$runtimeLines = @($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|runtime\|Python\|' })
if ($runtimeLines.Count -ne 1) { throw 'The real validator must emit exactly one Python observation.' }
$runtime = ([string]$runtimeLines[0]).Substring('SKYVIEW_EVENT|runtime|Python|'.Length) | ConvertFrom-Json
if ($runtime.component -ne 'Python' -or $runtime.requiredFamily -ne '3.14') { throw 'Wrong production Python requirement.' }
$pythonPass = @($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|validation\|PASS\|Python:' })
$pythonFail = @($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|validation\|FAIL\|Python:' })
if ($runtime.status -eq 'passed') {
    if ($pythonPass.Count -ne 1 -or $pythonFail.Count -ne 0 -or -not $runtime.version -or -not $runtime.executable -or -not $runtime.pipVersion) { throw 'Python pass is not backed by complete paired evidence.' }
} elseif ($runtime.status -in @('notFound','unusable','incomplete')) {
    if ($pythonFail.Count -ne 1 -or $pythonPass.Count -ne 0) { throw 'Incomplete/failed Python was presented as passing.' }
} else { throw 'Unknown production Python verification state.' }
$nodeLines=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|runtime\|Node.js\|' })
if ($nodeLines.Count -ne 1) { throw 'The real validator must emit exactly one Node/npm observation.' }
$node=([string]$nodeLines[0]).Substring('SKYVIEW_EVENT|runtime|Node.js|'.Length) | ConvertFrom-Json
if ($node.schema -ne 1 -or $node.component -ne 'Node.js' -or $node.requiredFamily -ne '24' -or $node.maintenanceEligibility -ne 'notEvaluated') { throw 'Node verification changed requirement or maintenance authority.' }
$nodePass=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|validation\|PASS\|Node.js:' })
$nodeFail=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|validation\|FAIL\|Node.js:' })
if ($node.status -eq 'passed') {
    if ($nodePass.Count -ne 1 -or $nodeFail.Count -ne 0 -or -not $node.version -or -not $node.executable -or -not $node.npmVersion -or -not $node.npmCli) { throw 'Node pass is missing complete paired evidence.' }
} elseif ($node.status -in @('notFound','unusable','incomplete')) {
    if ($nodeFail.Count -ne 1 -or $nodePass.Count -ne 0) { throw 'Incomplete/failed Node was presented as passing.' }
} else { throw 'Unknown Node verification state.' }
Write-Host 'SDE_WINDOWS_NODE_RUNTIME_VALIDATOR_OK'
Write-Host 'SDE_WINDOWS_PYTHON_RUNTIME_VALIDATOR_OK'
$gitLines=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|preferences\|Git\|' })
if ($gitLines.Count -ne 1) { throw 'The real validator must emit one Git preference observation.' }
$gitPreferences=([string]$gitLines[0]).Substring('SKYVIEW_EVENT|preferences|Git|'.Length) | ConvertFrom-Json
if ($gitPreferences.schema -ne 1 -or $gitPreferences.scope -ne 'globalOutsideRepository') { throw 'Wrong Git observation contract.' }
$gitPass=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|validation\|PASS\|Git:' })
$gitFail=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|validation\|FAIL\|Git:' })
if ($gitPreferences.status -eq 'passed') {
    if ($gitPass.Count -ne 1 -or $gitFail.Count -ne 0 -or @($gitPreferences.preferences | Where-Object status -eq 'unreadable').Count) { throw 'Unverified Git was reported Passed.' }
} elseif ($gitPass.Count -ne 0 -or $gitFail.Count -ne 1) { throw 'Missing/incomplete Git must fail its required check.' }
Write-Host 'SDE_WINDOWS_GIT_PREFERENCES_VALIDATOR_OK'
$editorLines=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|preferences\|VSCodium\|' })
if ($editorLines.Count -ne 1) { throw 'The real validator must emit one editor preference observation.' }
$editor=([string]$editorLines[0]).Substring('SKYVIEW_EVENT|preferences|VSCodium|'.Length) | ConvertFrom-Json
if ($editor.schema -ne 1 -or $editor.component -ne 'VSCodium' -or $editor.scope -ne 'standardUserFile') { throw 'Wrong editor observation scope.' }
if ($editor.status -notin @('read','missing','unreadable','invalid','unavailable')) { throw 'Unknown editor observation status.' }
if ($lines -match '^SKYVIEW_EVENT\|validation\|FAIL\|VSCodium settings (present|file missing)') { throw 'Optional settings still fail required editor functionality.' }
Write-Host 'SDE_WINDOWS_EDITOR_PREFERENCES_VALIDATOR_OK'
$locations=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|application\|VSCodium\|' })
if ($locations.Count -ne 1) { throw 'The real validator must emit one editor location observation.' }
$location=([string]$locations[0]).Substring('SKYVIEW_EVENT|application|VSCodium|'.Length) | ConvertFrom-Json
$locationPass=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|validation\|PASS\|VSCodium:' })
$locationFail=@($lines | Where-Object { [string]$_ -match '^SKYVIEW_EVENT\|validation\|FAIL\|VSCodium:' })
if ($location.schema -ne 1 -or $location.platform -ne 'windows') { throw 'Wrong editor location contract.' }
if ($location.status -eq 'verified') {
    if ($locationPass.Count -ne 1 -or -not $location.selectionId) { throw 'Editor pass lacks a verified selection.' }
} elseif ($locationPass.Count -or $locationFail.Count -ne 1) { throw 'Unverified editor was reported as passed.' }
Write-Host 'SDE_WINDOWS_EDITOR_LOCATION_VALIDATOR_OK'

Write-Host 'PowerShell parsing and real validator exit contract passed.'
& (Join-Path $PSScriptRoot 'Test-Node24Policy.ps1')
& (Join-Path $PSScriptRoot 'Test-PythonRuntime.ps1')
& (Join-Path $PSScriptRoot 'Test-NodeRuntime.ps1')
& (Join-Path $PSScriptRoot 'Test-GitPreferences.ps1')
& (Join-Path $PSScriptRoot 'Test-EditorPreferences.ps1')
& (Join-Path $PSScriptRoot 'Test-EditorLocation.ps1')
$global:LASTEXITCODE = 0
