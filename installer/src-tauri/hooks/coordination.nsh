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
!macroend
