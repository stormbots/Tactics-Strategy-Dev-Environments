; Change only existing shortcuts targeting this installation. A versioned ICO
; avoids reusing the Shell cache entry for the stable executable filename.
!macro SDE_SET_SHORTCUT_ICON shortcut
  !insertmacro IsShortcutTarget "${shortcut}" "$INSTDIR\${MAINBINARYNAME}.exe"
  Pop $0
  ${If} $0 = 1
    !insertmacro ComHlpr_CreateInProcInstance ${CLSID_ShellLink} ${IID_IShellLink} r0 ""
    ${If} $0 P<> 0
      ${IUnknown::QueryInterface} $0 '("${IID_IPersistFile}",.r1)'
      ${If} $1 P<> 0
        ${IPersistFile::Load} $1 '("${shortcut}", ${STGM_READWRITE})'
        ${IShellLink::SetIconLocation} $0 '(w "$INSTDIR\app-icons\skyview-dev-setup-${VERSION}.ico",i0)'
        ${IPersistFile::Save} $1 '("${shortcut}",1)'
        ${IUnknown::Release} $1 ""
      ${EndIf}
      ${IUnknown::Release} $0 ""
    ${EndIf}
  ${EndIf}
!macroend

!macro NSIS_HOOK_POSTINSTALL
  ; Record only numeric launch results, never keys or package output. ExecWait
  ; also supports GUI-subsystem executables without nsExec's console plumbing.
  FileOpen $1 "$INSTDIR\sde-bootstrap.log" w
  StrCpy $0 "launch-error"
  ClearErrors
  ExecWait '"$INSTDIR\skyview-dev-setup.exe" --coordination-init' $0
  FileWrite $1 "coordination=$0$\r$\n"
  ${If} ${Errors}
    FileClose $1
    Abort "SDE coordination could not start."
  ${EndIf}
  ${If} $0 != 0
    FileClose $1
    Abort "SDE coordination could not be initialized."
  ${EndIf}
  ; A 32-bit NSIS host uses Sysnative; a native host uses System32.
  StrCpy $0 "launch-error"
  ClearErrors
  IfFileExists "C:\Windows\Sysnative\WindowsPowerShell\v1.0\powershell.exe" 0 sde_system32_shell
  ExecWait '"C:\Windows\Sysnative\WindowsPowerShell\v1.0\powershell.exe" -WindowStyle Hidden -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$INSTDIR\backend\windows\self-update\Bootstrap-SkyviewSelfUpdate.ps1"' $0
  Goto sde_shell_done
  sde_system32_shell:
  ExecWait '"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -WindowStyle Hidden -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$INSTDIR\backend\windows\self-update\Bootstrap-SkyviewSelfUpdate.ps1"' $0
  sde_shell_done:
  FileWrite $1 "maintenance=$0$\r$\n"
  FileClose $1
  ${If} ${Errors}
    Abort "SDE maintenance bootstrap could not start."
  ${EndIf}
  ${If} $0 != 0
    Abort "SDE maintenance bootstrap failed; mentor review is required."
  ${EndIf}
  !insertmacro SDE_SET_SHORTCUT_ICON "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk"
  !insertmacro SDE_SET_SHORTCUT_ICON "$SMPROGRAMS\${PRODUCTNAME}.lnk"
  !insertmacro SDE_SET_SHORTCUT_ICON "$DESKTOP\${PRODUCTNAME}.lnk"
  ; Notify already-running Shell processes after updating shortcut metadata.
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0x1000, p 0, p 0)'
!macroend
