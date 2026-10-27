$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Coordination process tests are restricted to disposable runners.' }
$root = 'C:\ProgramData\SkyviewRoboticsCoordination'
$journal = Join-Path $root 'transaction.json'
$engine = (Resolve-Path (Join-Path $PSScriptRoot '../windows/chocolatey/tools/Coordination.ps1')).Path
. $engine
if (Test-Path $journal) { throw 'Unexpected transaction at fixture start.' }
Invoke-SkyviewCoordinated -Mutation -Action {
    Invoke-SkyviewCoordinated -Action { Write-Host 'SAME_PROCESS_NESTING_OK' }
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command ". '$engine'; Invoke-SkyviewCoordinated -Mutation -Action { Write-Output 'CHILD_TRANSACTION_OK' }"
    if ($LASTEXITCODE -ne 0) { throw 'Child could not reuse its authenticated transaction.' }
}
if (Test-Path $journal) { throw 'Normal completion left a transaction record.' }
$fixture = Join-Path 'C:\Users\Public' ('Skyview coordination probe ' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $fixture | Out-Null
Copy-Item $engine (Join-Path $fixture 'Coordination.ps1')
$probe = Join-Path $fixture 'probe.ps1'
@'
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Coordination.ps1')
Invoke-SkyviewCoordinated -Mutation -Action {
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'ready'), 'ready')
    Start-Sleep -Seconds 60
}
'@ | Set-Content $probe -Encoding UTF8
$holder = Start-Process powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',"`"$probe`"") -PassThru -WindowStyle Hidden
try {
    $limit = [DateTime]::UtcNow.AddSeconds(15)
    while (-not (Test-Path (Join-Path $fixture 'ready')) -and [DateTime]::UtcNow -lt $limit) { Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path (Join-Path $fixture 'ready'))) { throw 'Holder did not acquire the transaction.' }
    $deferred = $false
    try { Invoke-SkyviewCoordinated -Mutation -Action { throw 'Conflicting action must not run.' } }
    catch { if ($_.Exception.Message -ne 'SKYVIEW_DEFERRED') { throw }; $deferred = $true }
    if (-not $deferred) { throw 'Concurrent operation was not deferred.' }
    $readDeferred = $false
    try { Invoke-SkyviewCoordinated -ReadOnly -Action { throw 'Validation must not overlap an active operation.' } }
    catch { if ($_.Exception.Message -ne 'SKYVIEW_DEFERRED') { throw }; $readDeferred = $true }
    if (-not $readDeferred) { throw 'Validation overlapped an active operation.' }
    # Terminate only our sleeping synthetic fixture; never a package transaction.
    $holder.Kill(); $holder.WaitForExit()
    if (-not (Test-Path $journal)) { throw 'Crash lost the protected transaction record.' }
    $blocked = $false
    try { Invoke-SkyviewCoordinated -Mutation -Action { throw 'Interrupted action must not run.' } }
    catch { if ($_.Exception.Message -notlike '*interrupted*mentor*') { throw }; $blocked = $true }
    if (-not $blocked) { throw 'An interrupted transaction was silently repeated.' }
    $journalBefore = [IO.File]::ReadAllBytes($journal)
    $incompatible = $false
    try { Invoke-SkyviewCoordinated -ReadOnly -Mutation -Action { throw 'Incompatible modes must not run.' } }
    catch { if ($_.Exception.Message -ne 'A changing operation cannot use read-only coordination.') { throw }; $incompatible = $true }
    if (-not $incompatible) { throw 'A mutation used read-only coordination.' }
    foreach ($name in @('Test-SkyviewStudentDev.ps1','Validate-SkyviewEnvironment.ps1')) {
        $validator = Join-Path $PSScriptRoot "../windows/chocolatey/tools/$name"
        # Real public validator entry points, without update/network discovery.
        # An incomplete disposable runner may fail readiness checks; it must
        # nevertheless emit its actual check results and completion summary.
        $output = @(& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $validator 2>&1)
        $validationExit = $LASTEXITCODE
        if ($validationExit -notin @(0,1)) { throw "Validation failed to run: $name exit=$validationExit" }
        if (-not ($output -match 'SKYVIEW_EVENT\|validation\|WARNING\|An interrupted system operation')) { throw "Validation lost the interruption warning: $name" }
        if (-not ($output -match 'SKYVIEW_EVENT\|summary\|')) { throw "Validation was blocked by the interrupted journal: $name" }
        if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($journal)) -ne [Convert]::ToBase64String($journalBefore)) { throw 'Read-only validation changed the interruption record.' }
    }
    $stillBlocked = $false
    try { Invoke-SkyviewCoordinated -Mutation -Action { throw 'Validation must not authorize another change.' } }
    catch { if ($_.Exception.Message -notlike '*interrupted*mentor*') { throw }; $stillBlocked = $true }
    if (-not $stillBlocked) { throw 'Validation cleared the mutation block.' }
    $security = Get-Acl $journal
    foreach ($rule in $security.Access) {
        if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544')) { throw 'Private transaction record was exposed.' }
    }
} finally {
    if (-not $holder.HasExited) { $holder.Kill(); $holder.WaitForExit() }
    $holder.Dispose()
    # Explicit fixture recovery only: there were no package children or changes.
    Remove-Item $journal -Force -ErrorAction SilentlyContinue
    Remove-Item $fixture -Recurse -Force
}
Write-Host 'WINDOWS_COORDINATION_SUPERVISION_OK'
