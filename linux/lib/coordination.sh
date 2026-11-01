# shellcheck shell=bash
# Shared operation wrapper. Paths come only from the script's own installation.
skyview_coordinate() {
  local mode="$1" engine capability
  shift
  if [[ -f "$SCRIPT_DIR/lib/coordination.py" ]]; then
    engine="$SCRIPT_DIR/lib/coordination.py"
  else
    engine=/usr/local/lib/skyview-student-dev/coordination.py
  fi
  if [[ -n "${SKYVIEW_SESSION_FD:-}" && -n "${SKYVIEW_OPERATION_FD:-}" ]]; then
    /usr/bin/python3 "$engine" check || exit "$?"
  elif [[ "$mode" == system ]]; then
    # Root-only installed native supervision, not elevation or an acknowledgment
    # flag. Real inherited descriptors above remain mandatory for nested calls.
    # No fallback to the legacy Python journal writer if the app is unavailable.
    if [[ ! -x /usr/bin/skyview-dev-setup ]]; then
      printf '%s\n' 'SKYVIEW_EVENT|error|coordination|Install or repair the SDE application before system changes.' >&2
      exit 76
    fi
    # Use an EXISTING non-GUI mode for compatibility negotiation. Older apps
    # ignore unknown flags and could otherwise start a root GUI instead of a
    # supervisor. Preparation may publish an incident, never consent or retire it.
    if ! capability="$(/usr/bin/skyview-dev-setup --coordination-init)" || [[ "$capability" != SDE_LINUX_SYSTEM_SUPERVISOR_V1 ]]; then
      printf '%s\n' 'SKYVIEW_EVENT|error|coordination|The installed SDE application does not provide compatible system supervision. Install or repair the application first.' >&2
      exit 76
    fi
    exec /usr/bin/skyview-dev-setup --supervise-linux-system "$SCRIPT_DIR/$(basename -- "$0")" "$@"
  elif [[ "$mode" == readonly ]]; then
    exec /usr/bin/python3 "$engine" run readonly /bin/bash "$SCRIPT_DIR/$(basename -- "$0")" "$@"
  else
    exec /usr/bin/python3 "$engine" run "$mode" /bin/bash "$0" "$@"
  fi
}
