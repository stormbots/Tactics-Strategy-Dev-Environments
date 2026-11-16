#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/coordination.sh
if [[ -f "$SCRIPT_DIR/lib/coordination.sh" ]]; then
  source "$SCRIPT_DIR/lib/coordination.sh"
else
  # shellcheck source=/usr/local/lib/skyview-student-dev/coordination.sh
  source /usr/local/lib/skyview-student-dev/coordination.sh
fi
skyview_coordinate readonly "$@"
if [[ -f "$SCRIPT_DIR/lib/common.sh" ]]; then
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
else
  # shellcheck source=/usr/local/lib/skyview-student-dev/common.sh
  source /usr/local/lib/skyview-student-dev/common.sh
fi
set +e

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

pass() { event validation PASS "$*"; printf 'PASS  %s\n' "$*"; PASS_COUNT=$((PASS_COUNT+1)); }
warnv() { event validation WARNING "$*"; printf 'WARN  %s\n' "$*"; WARN_COUNT=$((WARN_COUNT+1)); }
fail() { event validation FAIL "$*"; printf 'FAIL  %s\n' "$*"; FAIL_COUNT=$((FAIL_COUNT+1)); }
info() { event validation INFO "$*"; printf 'INFO  %s\n' "$*"; }

check_command() {
  local cmd="$1" label="${2:-$1}"
  if command -v "$cmd" >/dev/null 2>&1; then
    local version=""
    case "$cmd" in
      git|gh|pwsh|python3.14) version="$("$cmd" --version 2>/dev/null | head -n1)" ;;
    esac
    pass "$label${version:+: $version}"
  else
    fail "$label not found"
  fi
}

printf '%s\n' "Skyview Robotics Student Dev Environment validation v${SKYVIEW_VERSION}"
printf '%s\n' "------------------------------------------------------------"

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  if [[ "${ID:-}" == "linuxmint" ]]; then
    pass "Linux Mint detected: ${PRETTY_NAME:-Linux Mint}"
  else
    fail "Expected Linux Mint; detected ${PRETTY_NAME:-unknown}"
  fi
else
  fail "/etc/os-release is unavailable"
fi

if [[ "${XDG_CURRENT_DESKTOP:-}" == *Cinnamon* || "${DESKTOP_SESSION:-}" == *cinnamon* ]]; then
  pass "Cinnamon desktop session detected"
else
  warnv "Cinnamon desktop session not detected in this shell"
fi

TARGET_USER="$(id -un)"
TARGET_HOME="$HOME"
[[ -n "$TARGET_HOME" ]] || TARGET_HOME="$HOME"
info "Configured student/shared user: ${TARGET_USER:-unknown} (${TARGET_HOME:-unknown})"

check_command gh "GitHub CLI"
check_command dbeaver DBeaver
check_command firefox Firefox
check_command pwsh "PowerShell 7"
check_command ssh OpenSSH
check_command 7z 7-Zip
check_command pycharm PyCharm

if command -v google-chrome >/dev/null 2>&1 || command -v google-chrome-stable >/dev/null 2>&1; then
  pass "Google Chrome found"
else
  if [[ "$(dpkg --print-architecture 2>/dev/null)" == "amd64" ]]; then
    fail "Google Chrome not found"
  else
    warnv "Google Chrome not found; automated Chrome parity is only enforced on amd64"
  fi
fi

# One selected interpreter owns every Node/npm probe. No bare npm fallback.
NODE_RUNTIME="$SCRIPT_DIR/lib/node_runtime.py"
[[ -f "$NODE_RUNTIME" ]] || NODE_RUNTIME="$SKYVIEW_LIB/node_runtime.py"
NODE_OUTPUT="$(/usr/bin/python3 "$NODE_RUNTIME")"
case "$?" in
  0) PASS_COUNT=$((PASS_COUNT+1)) ;;
  10) FAIL_COUNT=$((FAIL_COUNT+1)) ;;
  *) fail "Node.js: SDE could not finish the Node check. Review the check details." ;;
esac
printf '%s\n' "$NODE_OUTPUT"
NODE_RECORD="${NODE_OUTPUT%%$'\n'*}"
NODE_RECORD="${NODE_RECORD#SKYVIEW_EVENT|runtime|Node.js|}"

# One explicit interpreter owns its temporary environment and project-local pip.
PYTHON_RUNTIME="$SCRIPT_DIR/lib/python_runtime.py"
[[ -f "$PYTHON_RUNTIME" ]] || PYTHON_RUNTIME="$SKYVIEW_LIB/python_runtime.py"
/usr/bin/python3 "$PYTHON_RUNTIME"
case "$?" in
  0) PASS_COUNT=$((PASS_COUNT+1)) ;;
  10) FAIL_COUNT=$((FAIL_COUNT+1)) ;;
  *) fail "Python: SDE could not finish the Python check. Review the check details." ;;
esac

# Required command/configuration checks are separate from recommendations.
GIT_PREFERENCES="$SCRIPT_DIR/lib/git_preferences.py"
[[ -f "$GIT_PREFERENCES" ]] || GIT_PREFERENCES="$SKYVIEW_LIB/git_preferences.py"
/usr/bin/python3 "$GIT_PREFERENCES"
case "$?" in
  0) PASS_COUNT=$((PASS_COUNT+1)) ;;
  10) FAIL_COUNT=$((FAIL_COUNT+1)) ;;
  *) fail "Git: SDE could not finish the Git check. Review the check details." ;;
esac
info "Git identity and GitHub sign-in are optional."

if [[ "${1:-}" == "--check-updates" ]] && command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    info "GitHub CLI is authenticated"
  else
    info "GitHub CLI is installed but intentionally not authenticated"
  fi
fi

if [[ -d "$TARGET_HOME/Development" ]]; then
  pass "Development workspace exists: $TARGET_HOME/Development"
else
  fail "Development workspace missing: $TARGET_HOME/Development"
fi

CODIUM_SETTINGS="${XDG_CONFIG_HOME:-$TARGET_HOME/.config}/VSCodium/User/settings.json"
EDITOR_PREFERENCES="$SCRIPT_DIR/lib/editor_preferences.py"
[[ -f "$EDITOR_PREFERENCES" ]] || EDITOR_PREFERENCES="$SKYVIEW_LIB/editor_preferences.py"
printf '%s' "$NODE_RECORD" | /usr/bin/python3 "$EDITOR_PREFERENCES" "$CODIUM_SETTINGS"
case "$?" in
  0) : ;;
  20) WARN_COUNT=$((WARN_COUNT+1)) ;;
  *) warnv "SDE could not finish checking VSCodium preferences. Your settings have not been changed." ;;
esac

EXT_FILE=""
[[ -f "$SKYVIEW_SHARE/extensions.txt" ]] && EXT_FILE="$SKYVIEW_SHARE/extensions.txt"
[[ -z "$EXT_FILE" && -f "$SCRIPT_DIR/extensions.txt" ]] && EXT_FILE="$SCRIPT_DIR/extensions.txt"
EDITOR_LOCATION="$SCRIPT_DIR/lib/editor_location.py"
[[ -f "$EDITOR_LOCATION" ]] || EDITOR_LOCATION="$SKYVIEW_LIB/editor_location.py"
EDITOR_OUTPUT="$(/usr/bin/python3 "$EDITOR_LOCATION" --validate "$EXT_FILE")"
EDITOR_EXIT=$?
printf '%s\n' "$EDITOR_OUTPUT"
# Preserve each required failure count from the helper's explicit records.
EDITOR_FAILURES=0
EDITOR_RESULTS=0
EDITOR_OBSERVATIONS=0
while IFS= read -r editor_line; do
  [[ "$editor_line" == SKYVIEW_EVENT\|validation\|PASS\|* ]] && PASS_COUNT=$((PASS_COUNT+1))
  [[ "$editor_line" == SKYVIEW_EVENT\|application\|VSCodium\|* ]] && EDITOR_OBSERVATIONS=$((EDITOR_OBSERVATIONS+1))
  [[ "$editor_line" == SKYVIEW_EVENT\|validation\|PASS\|VSCodium:* || "$editor_line" == SKYVIEW_EVENT\|validation\|FAIL\|VSCodium:* ]] && EDITOR_RESULTS=$((EDITOR_RESULTS+1))
  if [[ "$editor_line" == SKYVIEW_EVENT\|validation\|FAIL\|* ]]; then
    FAIL_COUNT=$((FAIL_COUNT+1)); EDITOR_FAILURES=$((EDITOR_FAILURES+1))
  fi
done <<< "$EDITOR_OUTPUT"
if [[ "$EDITOR_RESULTS" -eq 0 || "$EDITOR_OBSERVATIONS" -ne 1 || ( "$EDITOR_EXIT" -ne 0 && "$EDITOR_FAILURES" -eq 0 ) ]]; then
  fail "VSCodium: SDE could not finish checking the editor installation."
fi
EDITOR_RECORD="${EDITOR_OUTPUT%%$'\n'*}"
EDITOR_RECORD="${EDITOR_RECORD#SKYVIEW_EVENT|application|VSCodium|}"

if systemctl is-enabled skyview-student-dev-update.timer >/dev/null 2>&1; then
  pass "Weekly maintenance timer is enabled"
else
  fail "Weekly maintenance timer is not enabled"
fi
if systemctl is-active skyview-student-dev-update.timer >/dev/null 2>&1; then
  pass "Weekly maintenance timer is active"
else
  fail "Weekly maintenance timer is not active"
fi

if [[ -L /opt/pycharm && -x /opt/pycharm/bin/pycharm ]]; then
  pass "PyCharm managed installation is active at /opt/pycharm"
else
  fail "Managed PyCharm installation/symlink is missing"
fi

REPO_FILE="$SKYVIEW_ETC/repositories.csv"
[[ -f "$REPO_FILE" ]] || REPO_FILE="$SCRIPT_DIR/repositories.csv"
if [[ -f "$REPO_FILE" ]]; then
  while IFS=, read -r name _url _branch enabled; do
    name="${name//\r/}"; enabled="${enabled//\r/}"
    [[ -z "$name" ]] && continue
    case "${enabled,,}" in
      1|true|yes|y)
        if [[ -d "$TARGET_HOME/Development/$name/.git" ]]; then
          pass "Configured repository cloned: $name"
        else
          fail "Configured repository missing: $TARGET_HOME/Development/$name"
        fi
        ;;
    esac
  done < <(tail -n +2 "$REPO_FILE")
fi

printf '%s\n' "------------------------------------------------------------"
TOOL_RECORDS="$SCRIPT_DIR/lib/tool_records.py"
[[ -f "$TOOL_RECORDS" ]] || TOOL_RECORDS="$SKYVIEW_LIB/tool_records.py"
printf '%s\n%s' "$NODE_RECORD" "$EDITOR_RECORD" | /usr/bin/python3 "$TOOL_RECORDS" "${1:-}" --runtime-observations || warnv "Tool version and update metadata is unavailable"
printf 'RESULT: %d PASS, %d WARN, %d FAIL\n' "$PASS_COUNT" "$WARN_COUNT" "$FAIL_COUNT"

event summary "$FAIL_COUNT" "$PASS_COUNT passed; $WARN_COUNT warnings; $FAIL_COUNT failed"
if (( FAIL_COUNT > 0 )); then
  exit 1
fi
exit 0
