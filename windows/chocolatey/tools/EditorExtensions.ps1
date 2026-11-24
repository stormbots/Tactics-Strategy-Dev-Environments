# Shared by the existing approved configuration entries. Inventory grants no launch/update authority.
function Install-SkyviewMissingEditorExtensions {
    param([Parameter(Mandatory=$true)][string]$Codium, [Parameter(Mandatory=$true)][string]$ListPath)
    $policy = Get-Item -LiteralPath $ListPath -ErrorAction Stop
    if ($policy.Length -gt 65536) { throw 'The required extension list is too large. No extensions were changed.' }
    $required = @()
    foreach ($line in @(Get-Content -LiteralPath $ListPath -ErrorAction Stop)) {
        $entry = $line.Trim()
        if (-not $entry -or $entry.StartsWith('#')) { continue }
        if ($entry.Length -gt 256 -or $entry -notmatch '\A[A-Za-z0-9][A-Za-z0-9._-]*\.[A-Za-z0-9][A-Za-z0-9._-]*\z') { throw 'The required extension list could not be read. No extensions were changed.' }
        $required += $entry
        if ($required.Count -gt 256) { throw 'The required extension list is too large. No extensions were changed.' }
    }
    if ($required.Count -eq 0) { return }
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $inventory = @(& $Codium --list-extensions 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) { Write-Host $_ }
            else { $_ }
        })
        $inventoryCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previous }
    if ($inventoryCode -ne 0 -or $inventory.Count -gt 4096 -or ($inventory -join "`n").Length -gt 1048576) { throw 'SDE could not read your installed VSCodium extensions. No extensions were changed. Check VSCodium and try again.' }
    $installed = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($line in $inventory) {
        $entry = ([string]$line).Trim()
        if (-not $entry) { continue }
        if ($entry.Length -gt 256 -or $entry -notmatch '\A[A-Za-z0-9][A-Za-z0-9._-]*\.[A-Za-z0-9][A-Za-z0-9._-]*\z') { throw 'SDE could not read your installed VSCodium extensions. No extensions were changed. Check VSCodium and try again.' }
        $null = $installed.Add($entry)
    }
    foreach ($extension in $required) {
        if ($installed.Contains($extension)) {
            Write-Host "Keeping installed VSCodium extension: $extension"
            continue
        }
        Write-Host "SKYVIEW_EVENT|phase|extensions|Installing missing editor extension $extension"
        $previous = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & $Codium --install-extension $extension 2>&1 | ForEach-Object { Write-Host $_ }
            $code = $LASTEXITCODE
        } finally { $ErrorActionPreference = $previous }
        if ($code -ne 0) { throw "Editor extension $extension failed with exit code $code." }
        $null = $installed.Add($extension)
    }
}
