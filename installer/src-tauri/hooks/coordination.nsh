!macro NSIS_HOOK_POSTINSTALL
  nsExec::ExecToLog '"$INSTDIR\skyview-dev-setup.exe" --coordination-init'
  Pop $0
  ${If} $0 != 0
    Abort "SDE coordination could not be initialized."
  ${EndIf}
!macroend
