$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
. (Join-Path $PSScriptRoot 'EditorLocation.ps1')
Get-SkyviewEditorLocation | ConvertTo-Json -Compress
