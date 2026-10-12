$ErrorActionPreference = 'Stop'
if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne 'S-1-5-18') { throw 'SYSTEM status publication required.' }
$path = 'C:\ProgramData\SkyviewRobotics\SelfUpdate\status.json'
$item = Get-Item -LiteralPath $path -Force
if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Untrusted status link.' }
$acl = New-Object Security.AccessControl.FileSecurity
$acl.SetSecurityDescriptorSddlForm('O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FR;;;BU)')
Set-Acl -LiteralPath $path -AclObject $acl
