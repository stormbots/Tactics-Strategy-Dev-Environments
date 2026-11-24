$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../windows/chocolatey/tools/EditorExtensions.ps1')
function Assert-Extension($condition,$message) { if (-not $condition) { throw $message } }
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('sde-extensions-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $fixture | Out-Null
try {
    $policy = Join-Path $fixture 'extensions.txt'
    $script:extensionCalls = [Collections.Generic.List[string]]::new()
    $script:inventory = @()
    $script:inventoryExit = 0
    $script:failedExtension = ''
    $script:queryWarning = $false
    function Invoke-ExtensionFixture {
        $script:extensionCalls.Add(($args -join '|'))
        $global:LASTEXITCODE = 0
        if ($args[0] -eq '--list-extensions') { if ($script:queryWarning) { Write-Error 'Synthetic harmless CLI stderr' }; $global:LASTEXITCODE=$script:inventoryExit; return $script:inventory }
        if ($args.Count -ne 2 -or $args[0] -ne '--install-extension') { throw 'Unexpected modifying CLI arguments.' }
        if ($args[1] -eq $script:failedExtension) { $global:LASTEXITCODE=23 }
    }
    function Run-ExtensionFixture { Install-SkyviewMissingEditorExtensions -Codium Invoke-ExtensionFixture -ListPath $policy }
    function Expect-ExtensionRefusal {
        $refused=$false
        try { Run-ExtensionFixture } catch { $refused=$true }
        Assert-Extension $refused 'Expected extension operation refusal.'
    }
    Set-Content -LiteralPath $policy -Value @('EditorConfig.EditorConfig','new.extension','NEW.EXTENSION') -Encoding UTF8
    $script:inventory=@('editorconfig.editorconfig','student.personal-extension')
    Run-ExtensionFixture
    Assert-Extension (($script:extensionCalls -join ',') -ceq '--list-extensions,--install-extension|new.extension') 'Existing, foreign or duplicate extension was changed.'
    $script:extensionCalls.Clear();$script:queryWarning=$true;$script:inventory=@('editorconfig.editorconfig','new.extension')
    Run-ExtensionFixture
    Assert-Extension (($script:extensionCalls -join ',') -ceq '--list-extensions') 'Benign stderr changed existing extensions.'
    $script:queryWarning=$false
    $script:extensionCalls.Clear()
    Set-Content -LiteralPath $policy -Value '# Empty controlled policy' -Encoding UTF8
    $script:inventoryExit=23
    Run-ExtensionFixture
    Assert-Extension ($script:extensionCalls.Count -eq 0) 'Empty policy queried extensions.'
    Set-Content -LiteralPath $policy -Value 'new.extension' -Encoding UTF8
    Expect-ExtensionRefusal
    Assert-Extension (($script:extensionCalls -join ',') -ceq '--list-extensions') 'Failed inventory caused an install.'
    $script:inventoryExit=0
    foreach ($malformed in @('not an extension','--bad-option',('a.'+('x'*257)))) {
        $script:extensionCalls.Clear();$script:inventory=@('keep.extension',$malformed)
        Expect-ExtensionRefusal
        Assert-Extension (($script:extensionCalls -join ',') -ceq '--list-extensions') 'Malformed inventory caused an install.'
    }
    foreach ($badPolicy in @("new.extension`nbad --option",(('x.y'+"`n")*257),('x'*65537))) {
        $script:extensionCalls.Clear()
        Set-Content -LiteralPath $policy -Value $badPolicy -Encoding UTF8
        Expect-ExtensionRefusal
        Assert-Extension ($script:extensionCalls.Count -eq 0) 'Invalid policy caused a CLI call.'
    }
    $script:extensionCalls.Clear();$script:inventory=@();$script:failedExtension='new.extension'
    Set-Content -LiteralPath $policy -Value @('new.extension','later.extension') -Encoding UTF8
    Expect-ExtensionRefusal
    Assert-Extension (($script:extensionCalls -join ',') -ceq '--list-extensions,--install-extension|new.extension') 'Failed install retried or changed later entries.'
    $global:LASTEXITCODE=0
    Write-Host 'SDE_EDITOR_EXTENSION_PRESERVATION_WINDOWS_OK'
} finally {
    Remove-Item -LiteralPath $fixture -Recurse -Force
    Remove-Item Function:Invoke-ExtensionFixture -ErrorAction SilentlyContinue
}
