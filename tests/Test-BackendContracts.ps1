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
Write-Host 'PowerShell parsing and real validator exit contract passed.'
$global:LASTEXITCODE = 0
