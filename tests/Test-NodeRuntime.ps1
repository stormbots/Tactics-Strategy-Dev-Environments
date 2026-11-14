$ErrorActionPreference='Stop'
$helper=Join-Path $PSScriptRoot '../windows/chocolatey/tools/NodeRuntime.ps1'
$probe=Join-Path $PSScriptRoot '../windows/chocolatey/tools/NodeRuntimeProbe.cjs'
. $helper
$prepared=Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1
# Real process adapter: quoting, failure, deadline and per-child environment isolation.
$beforeOptions=$env:NODE_OPTIONS
$beforePath=$env:PATH
try {
    $env:NODE_OPTIONS='--require ./sde-unexpected-project-module.cjs'
    $identity=Invoke-SkyviewNodeQuery $prepared.Source @($probe,'identity') 5000
    if ($identity.Code -ne 0 -or -not ($identity.Text | ConvertFrom-Json).executable) { throw 'Node probe inherited project injection or lost its output.' }
    if ($env:NODE_OPTIONS -ne '--require ./sde-unexpected-project-module.cjs') { throw 'Probe changed parent environment.' }
} finally { $env:NODE_OPTIONS=$beforeOptions }
$result=Invoke-SkyviewNodeQuery $prepared.Source @('--eval','process.stdout.write("path with spaces: " + String.fromCharCode(34) + "ok" + String.fromCharCode(34))') 5000
if ($result.Code -ne 0 -or $result.Text -ne 'path with spaces: "ok"') { throw 'Node probe argument quoting failed.' }
if ((Invoke-SkyviewNodeQuery $prepared.Source @('--eval','process.exit(7)') 5000).Code -ne 7) { throw 'Node exit code was lost.' }
if ((Invoke-SkyviewNodeQuery $prepared.Source @('--eval','setTimeout(()=>{},10000)') 100).Reason -ne 'timeout') { throw 'Node diagnostic deadline was not enforced.' }
& $prepared.Source (Join-Path $PSScriptRoot 'test_node_runtime_probe.cjs')
if ($LASTEXITCODE -ne 0) { throw 'Node/npm compatibility probe contracts failed.' }

$script:nodeChecks=0
function Assert-Node($Condition,[string]$Message) { if (-not $Condition) { throw $Message }; $script:nodeChecks++ }
function Reset-NodeCase {
    $script:nodePaths=@('C:\Node 24\node.exe','C:\Node26\node.exe')
    $script:nodeVersions=@{'C:\Node 24\node.exe'='24.19.0';'C:\Node26\node.exe'='26.1.0';'C:\shim\node.exe'='24.19.0'}
    $script:nodeComplete=$true
    $script:nodeCalls=New-Object 'System.Collections.Generic.List[object]'
    $script:npmVersion='11.9.0';$script:npmText='11.9.0'
    $script:nodeFail='';$script:nodeReason='completed';$script:wrongCli=$false
    $script:nodeMalformed=$false;$script:nodeShim=$false
}
function Get-SkyviewNodeCandidates { return [pscustomobject]@{Paths=$script:nodePaths;RequiredPaths=@('C:\Node 24\node.exe');Complete=$script:nodeComplete} }
function Test-SkyviewNodeExecutable([string]$Path) { return $script:nodeVersions.ContainsKey($Path) }
function Invoke-SkyviewNodeQuery {
    param([string]$Executable,[string[]]$Arguments,[int]$TimeoutMs)
    Assert-Node ($TimeoutMs -gt 0 -and $TimeoutMs -le 2500) 'Lost probe budget.'
    $stage=if ($Arguments[-1] -eq '--version') { 'version' } else { $Arguments[-1] }
    $script:nodeCalls.Add([pscustomobject]@{Executable=$Executable;Arguments=$Arguments;Stage=$stage})
    if ($stage -eq $script:nodeFail) { return @{Code=1;Text='';Reason=$script:nodeReason} }
    if ($stage -eq 'version') { return @{Code=0;Text=$script:npmText;Reason='completed'} }
    if ($script:nodeMalformed) { return @{Code=0;Text='not JSON';Reason='completed'} }
    $selected=if ($script:nodeShim -and $Executable -eq 'C:\shim\node.exe') { 'C:\Node 24\node.exe' } else { $Executable }
    $record=@{version=$script:nodeVersions[$selected];executable=$selected}
    if ($stage -eq 'npm') {
        $record.npmVersion=$script:npmVersion
        $record.npmCli=if ($script:wrongCli) { 'C:\Node26\node_modules\npm\bin\npm-cli.js' } else { 'C:\Node 24\node_modules\npm\bin\npm-cli.js' }
    }
    return @{Code=0;Text=($record | ConvertTo-Json -Compress);Reason='completed'}
}
try {
    Reset-NodeCase
    $node=Get-SkyviewNodeRuntime
    Assert-Node ($node.status -eq 'passed' -and $node.version -eq '24.19.0' -and $node.npmVersion -eq '11.9.0') 'Compatible pair did not pass.'
    Assert-Node ($node.maintenanceEligibility -eq 'notEvaluated') 'Validation acquired maintenance authority.'
    Assert-Node (@($script:nodeCalls | Where-Object {$_.Executable -ne 'C:\Node 24\node.exe'}).Count -eq 0) 'Another default or bare npm was executed.'
    $script:nodeVersions['C:\Node26\node.exe']='20.19.0'
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'passed') 'Older default rejected a valid pair.'

    Reset-NodeCase;$script:nodePaths=@('C:\Node26\node.exe','C:\Node 24\node.exe')
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'passed') 'Fallback could not find side-by-side Node.'
    Reset-NodeCase;$script:nodePaths=@('C:\shim\node.exe');$script:nodeShim=$true
    $node=Get-SkyviewNodeRuntime
    Assert-Node ($node.status -eq 'passed' -and $node.executable -eq 'C:\Node 24\node.exe') 'Executable shim was not resolved and reverified.'
    Assert-Node (@($script:nodeCalls | Where-Object {$_.Stage -ne 'identity' -and $_.Executable -ne 'C:\Node 24\node.exe'}).Count -eq 0) 'npm used a manager shim instead of the verified interpreter.'

    Reset-NodeCase;$script:nodePaths=@('C:\Node26\node.exe')
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'notFound') 'Completed search of another family was not distinct.'
    $script:nodeComplete=$false
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'incomplete') 'Discovery failure was called missing.'
    Reset-NodeCase;$script:nodeMalformed=$true
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'incomplete') 'Malformed output was accepted.'
    Reset-NodeCase;$script:nodeFail='identity'
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'unusable') 'Registered unusable Node was called verified or missing.'
    Reset-NodeCase;$script:nodeComplete=$false
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'passed') 'An unrelated discovery failure rejected a complete pair.'

    foreach ($stage in @('npm','version')) {
        Reset-NodeCase;$script:nodeFail=$stage
        $node=Get-SkyviewNodeRuntime
        Assert-Node ($node.status -eq 'unusable' -and $node.reason -eq 'npmFailed') 'Missing/broken npm was accepted.'
        Reset-NodeCase;$script:nodeFail=$stage;$script:nodeReason='timeout'
        $node=Get-SkyviewNodeRuntime
        Assert-Node ($node.status -eq 'incomplete' -and $node.reason -eq 'npmTimeout') 'npm timeout was relabeled absence.'
    }
    Reset-NodeCase;$script:wrongCli=$true
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'unusable') 'Another installation supplied an npm pass.'
    Reset-NodeCase;$script:npmText='12.0.0'
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'unusable') 'CLI output disagreed with its checked package version.'
    Reset-NodeCase;$script:npmVersion='12.0.0-beta.1';$script:npmText=$script:npmVersion
    Assert-Node ((Get-SkyviewNodeRuntime).status -eq 'passed') 'A compatible npm acquired an unapproved release-family restriction.'
    Assert-Node ($env:PATH -ceq $beforePath -and $env:NODE_OPTIONS -ceq $beforeOptions) 'Verification changed parent defaults.'
} finally { . $helper }
if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
    # Read real Windows directory stores without running the fake executables.
    $fixture=Join-Path ([IO.Path]::GetTempPath()) ('SDE Node stores ' + [guid]::NewGuid())
    $saved=@{NVM_HOME=$env:NVM_HOME;VOLTA_HOME=$env:VOLTA_HOME;FNM_DIR=$env:FNM_DIR}
    try {
        $env:NVM_HOME=Join-Path $fixture 'nvm';$env:VOLTA_HOME=Join-Path $fixture 'volta';$env:FNM_DIR=Join-Path $fixture 'fnm'
        $locations=@((Join-Path $env:NVM_HOME 'v24.19.0\node.exe'),(Join-Path $env:VOLTA_HOME 'tools\image\node\24.20.0\node.exe'),(Join-Path $env:FNM_DIR 'node-versions\v24.21.0\installation\node.exe'))
        foreach ($location in $locations) {
            New-Item -ItemType Directory -Path (Split-Path $location -Parent) -Force | Out-Null
            [IO.File]::WriteAllText($location,'Discovery only; never execute this fixture')
        }
        $found=Get-SkyviewNodeCandidates
        foreach ($location in $locations) { Assert-Node ($found.Paths -contains $location) 'Recognized manager store was not discovered.' }
        Assert-Node ($env:PATH -ceq $beforePath) 'Store discovery switched the default.'
    } finally {
        $env:NVM_HOME=$saved.NVM_HOME;$env:VOLTA_HOME=$saved.VOLTA_HOME;$env:FNM_DIR=$saved.FNM_DIR
        if (Test-Path -LiteralPath $fixture) { Remove-Item -LiteralPath $fixture -Recurse -Force }
    }
    $node=Get-SkyviewNodeRuntime
    Assert-Node ($node.status -eq 'passed' -and $node.version -match '^24\.' -and $node.npmVersion -and $node.npmCli) 'Prepared Windows Node 24/npm pair did not verify.'
    Write-Host 'WINDOWS_NODE_RUNTIME_NATIVE_OBSERVED passed'
}
Write-Host "NODE_RUNTIME_CONTRACTS_OK ($script:nodeChecks assertions)"
