# Advisory only. Installed versions come from the completed local validation snapshot.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
. (Join-Path $PSScriptRoot 'ToolRecords.ps1')
$inputRows = [Console]::In.ReadToEnd() | ConvertFrom-Json
$installed = @{}
foreach ($row in $inputRows) { if ($row.installedVersion) { $installed[[string]$row.tool]=[string]$row.installedVersion } }
$records = @(Get-SkyviewToolRecords -Installed $installed -CheckUpdates $true)
ConvertTo-Json -InputObject $records -Compress
