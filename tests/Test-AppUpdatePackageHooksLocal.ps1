# Local syntax / scope-parser checks only. Never execute the packaging main block.
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot '../windows/self-update/Bootstrap-SkyviewSelfUpdate.ps1'
$tokens = $null
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile((Resolve-Path $source),[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$function = $ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'ConvertFrom-AppOnlyIntentBytes'},$true)
if (-not $function) { throw 'Scope parser missing.' }
# Load only the pure parser, not the privileged packaging entry point.
. ([scriptblock]::Create($function.Extent.Text))
$utf8 = New-Object Text.UTF8Encoding($false,$true)
foreach ($case in @(@{ Text = '{"schema":1,"kind":"installation","scope":"app_only"}'; Expected = $true })) {
    $actual = ConvertFrom-AppOnlyIntentBytes ($utf8.GetBytes($case.Text))
    if ($actual -isnot [bool] -or $actual -ne $case.Expected) { throw 'Wrong scope decision.' }
}
$rejections = @(
    '{"schema":1,"kind":"installation"}', '{"schema":1,"kind":"system","token":"legacy"}',
    '[]', 'null', '{', '{"schema":true}', '{"schema":"1"}', '{"schema":2}',
    '{"schema":1,"scope":"future"}',
    '{"schema":1,"scope":"APP_ONLY","kind":"installation"}',
    '{"schema":1,"scope":["app_only"],"kind":"installation"}',
    '{"schema":1,"scope":"app_only","kind":"system"}'
)
foreach ($text in $rejections) {
    $rejected = $false
    try { $null = ConvertFrom-AppOnlyIntentBytes ($utf8.GetBytes($text)) } catch { $rejected = $true }
    if (-not $rejected) { throw "Invalid record accepted: $text" }
}
foreach ($bytes in @((New-Object byte[] 4097), [byte[]]@(255))) {
    $rejected = $false
    try { $null = ConvertFrom-AppOnlyIntentBytes $bytes } catch { $rejected = $true }
    if (-not $rejected) { throw 'Bounds or UTF-8 validation failed.' }
}
Write-Output 'WINDOWS_HOOK_LOCAL_SYNTAX_AND_15_SCOPE_CASES_OK (no Windows runtime/ACL/task validation)'
