!macro NSIS_HOOK_POSTINSTALL
  nsExec::ExecToLog '"$INSTDIR\skyview-dev-setup.exe" --coordination-init'
  Pop $0
  ${If} $0 != 0
    Abort "SDE coordination could not be initialized."
  ${EndIf}
  nsExec::ExecToLog '"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$INSTDIR\backend\windows\self-update\Bootstrap-SkyviewSelfUpdate.ps1"'
  Pop $0
  ${If} $0 != 0
    Abort "SDE maintenance bootstrap failed; mentor review is required."
  ${EndIf}
!macroend
