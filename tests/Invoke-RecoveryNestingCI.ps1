param([Parameter(Mandatory=$true)][string]$FixtureRoot)
# Called only by the native coordinator suite, never by the application.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $FixtureRoot -notmatch '^C:\\ProgramData\\coordination-test-[0-9]+-[0-9]+$') { throw 'Disposable native fixture required.' }
Import-Module "$PSHOME\Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1" -ErrorAction Stop
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/Coordination.ps1')
$script:SkyviewCoordinationRoot = $FixtureRoot
Invoke-SkyviewCoordinated -Mutation -RequireParent -Action {
    Write-Output 'SDE_RECOVERY_EXISTING_WINDOWS_NESTING_OK'
}
