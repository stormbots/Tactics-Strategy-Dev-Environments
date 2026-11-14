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
Write-Host 'SDE_WINDOWS_PYTHON_RUNTIME_VALIDATOR_OK'
Write-Host 'PowerShell parsing and real validator exit contract passed.'
& (Join-Path $PSScriptRoot 'Test-Node24Policy.ps1')
& (Join-Path $PSScriptRoot 'Test-PythonRuntime.ps1')
$global:LASTEXITCODE = 0
