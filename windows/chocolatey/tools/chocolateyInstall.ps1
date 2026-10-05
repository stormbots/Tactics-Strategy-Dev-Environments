$ErrorActionPreference = 'Stop'

$Skyview = 'C:\ProgramData\SkyviewRobotics'
$Logs = Join-Path $Skyview 'Logs'
$Tools = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ChocolateyLog = 'C:\ProgramData\chocolatey\logs\chocolatey.log'
$ConfigStages = 10

function Invoke-ConfigStage {
    param(
        [int]$Number,
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host ("[Config {0}/{1}] {2}..." -f $Number, $ConfigStages, $Name) -ForegroundColor Cyan
    try {
        & $Action
        Write-Host ("[Config {0}/{1}] OK" -f $Number, $ConfigStages) -ForegroundColor Green
    }
    catch {
        Write-Host ("[Config {0}/{1}] FAILED: {2}" -f $Number, $ConfigStages, $_.Exception.Message) -ForegroundColor Red
        Write-Host "Chocolatey log: $ChocolateyLog"
        throw
    }
}

Write-Host 'Configuring Skyview Robotics Windows development workstation...'

Invoke-ConfigStage 1 'Creating Skyview and development directories' {
    New-Item -ItemType Directory -Path $Skyview -Force | Out-Null
    New-Item -ItemType Directory -Path $Logs -Force | Out-Null
    New-Item -ItemType Directory -Path 'C:\Development' -Force | Out-Null
}

Invoke-ConfigStage 2 'Copying Skyview maintenance and validation files' {
    foreach ($file in @(
        'AutoUpdate-SkyviewTools.ps1',
        'Update-SkyviewTools.ps1',
        'Update-Node24.ps1',
        'Setup-SkyviewRepositories.ps1',
        'Test-SkyviewStudentDev.ps1',
        'extensions.txt',
        'repositories.csv'
    )) {
        Copy-Item (Join-Path $Tools $file) (Join-Path $Skyview $file) -Force
    }
}

Invoke-ConfigStage 3 'Enabling Windows long-path support' {
    $fsKey = 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem'
    Set-ItemProperty -Path $fsKey -Name LongPathsEnabled -Type DWord -Value 1
}

Invoke-ConfigStage 4 'Enabling Windows Developer Mode setting' {
    $appUnlock = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock'
    if (-not (Test-Path $appUnlock)) {
        New-Item -Path $appUnlock -Force | Out-Null
    }
    Set-ItemProperty -Path $appUnlock -Name AllowDevelopmentWithoutDevLicense -Type DWord -Value 1
}

Invoke-ConfigStage 5 'Showing file extensions in File Explorer' {
    $explorer = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'
    # On a normal Windows profile this key already exists. Recreating an existing
    # Explorer key with New-Item -Force can raise UnauthorizedAccessException even
    # in an elevated session, so only create it when it is genuinely absent.
    if (-not (Test-Path $explorer)) {
        New-Item -Path $explorer -Force | Out-Null
    }
    Set-ItemProperty -Path $explorer -Name HideFileExt -Type DWord -Value 0
}

Invoke-ConfigStage 6 'Ensuring the Windows OpenSSH client is installed' {
    $ssh = Get-WindowsCapability -Online -Name 'OpenSSH.Client*' -ErrorAction SilentlyContinue
    if ($ssh -and $ssh.State -ne 'Installed') {
        Add-WindowsCapability -Online -Name $ssh.Name | Out-Null
    }

    if (Get-Command Update-SessionEnvironment -ErrorAction SilentlyContinue) {
        Update-SessionEnvironment
    }
}

Invoke-ConfigStage 7 'Applying team Git defaults' {
    if (Get-Command git.exe -ErrorAction SilentlyContinue) {
        git config --system core.longpaths true
        git config --global init.defaultBranch main
        git config --global fetch.prune true
    }
}

Invoke-ConfigStage 8 'Pinning Node.js major-version updates' {
    $choco = 'C:\ProgramData\chocolatey\bin\choco.exe'
    if (Test-Path $choco) {
        & $choco pin add --name=nodejs-lts | Out-Null
    }
}

Invoke-ConfigStage 9 'Configuring VSCodium and standard extensions' {
    $codium = Get-Command codium -ErrorAction SilentlyContinue
    $codiumPath = $null

    if (-not $codium) {
        $candidates = @(
            'C:\Program Files\VSCodium\bin\codium.cmd',
            'C:\Program Files\VSCodium\bin\codium.exe',
            "$env:LOCALAPPDATA\Programs\VSCodium\bin\codium.cmd"
        ) | Where-Object { Test-Path $_ }
        if ($candidates) { $codiumPath = $candidates[0] }
    }
    else {
        $codiumPath = $codium.Source
    }

    if ($codiumPath) {
        foreach ($ext in (Get-Content (Join-Path $Tools 'extensions.txt') | Where-Object { $_ })) {
            Write-Host "  Installing VSCodium extension $ext"

            # VSCodium can emit harmless Node.js deprecation warnings on stderr even
            # when the extension installation succeeds. Under Windows PowerShell 5.1,
            # $ErrorActionPreference='Stop' can promote that native stderr output into
            # a terminating PowerShell error. Temporarily relax the preference for the
            # native VSCodium process and use its exit code as the success criterion.
            $previousErrorActionPreference = $ErrorActionPreference
            try {
                $ErrorActionPreference = 'Continue'
                & $codiumPath --install-extension $ext --force 2>&1 | ForEach-Object {
                    Write-Host "    $_"
                }
                $codiumExit = $LASTEXITCODE
            }
            finally {
                $ErrorActionPreference = $previousErrorActionPreference
            }

            if ($codiumExit -ne 0) {
                Write-Warning "Extension install failed: $ext (exit code $codiumExit)"
            }
        }
    }
    else {
        Write-Warning 'VSCodium CLI was not found during package installation. Run the validation script after sign-out/sign-in.'
    }

    $settingsDir = Join-Path $env:APPDATA 'VSCodium\User'
    New-Item -ItemType Directory -Path $settingsDir -Force | Out-Null
    Copy-Item (Join-Path $Tools 'settings.json') (Join-Path $settingsDir 'settings.json') -Force
}

Invoke-ConfigStage 10 'Registering weekly development-tool updates' {
    $taskName = 'Skyview Robotics - Dev Tool Updates'
    $script = Join-Path $Skyview 'AutoUpdate-SkyviewTools.ps1'
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3:00am
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
}

Write-Host ''
Write-Host 'Skyview Robotics development workstation baseline installed.' -ForegroundColor Green
Write-Host 'Node.js is pinned to major 24 and Git/GitHub identity is intentionally unconfigured.'
Write-Host 'Run C:\ProgramData\SkyviewRobotics\Test-SkyviewStudentDev.ps1 to validate.'
