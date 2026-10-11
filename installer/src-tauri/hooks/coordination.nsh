!macro NSIS_HOOK_POSTINSTALL
  nsExec::ExecToLog '"$INSTDIR\skyview-dev-setup.exe" --coordination-init'
  Pop $0
  ${If} $0 != 0
    Abort "SDE coordination could not be initialized."
  ${EndIf}
  ; NSIS may be a 32-bit host on 64-bit Windows. Sysnative selects the
  ; native shell without leaving filesystem redirection disabled during a wait.
  IfFileExists "C:\Windows\Sysnative\WindowsPowerShell\v1.0\powershell.exe" 0 sde_system32_shell
  nsExec::ExecToLog '"C:\Windows\Sysnative\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$INSTDIR\backend\windows\self-update\Bootstrap-SkyviewSelfUpdate.ps1"'
  Goto sde_shell_done
  sde_system32_shell:
  nsExec::ExecToLog '"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$INSTDIR\backend\windows\self-update\Bootstrap-SkyviewSelfUpdate.ps1"'
  sde_shell_done:
  Pop $0
  ${If} $0 != 0
    Abort "SDE maintenance bootstrap failed; mentor review is required."
  ${EndIf}
!macroend
