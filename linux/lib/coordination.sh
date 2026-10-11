# shellcheck shell=bash
# Shared operation wrapper. Paths come only from the script's own installation.
skyview_coordinate() {
  local mode="$1" engine
  shift
  if [[ -f "$SCRIPT_DIR/lib/coordination.py" ]]; then
    engine="$SCRIPT_DIR/lib/coordination.py"
  else
    engine=/usr/local/lib/skyview-student-dev/coordination.py
  fi
  if [[ -n "${SKYVIEW_SESSION_FD:-}" && -n "${SKYVIEW_OPERATION_FD:-}" ]]; then
    /usr/bin/python3 "$engine" check || exit "$?"
  else
    exec /usr/bin/python3 "$engine" run "$mode" /bin/bash "$0" "$@"
  fi
}
