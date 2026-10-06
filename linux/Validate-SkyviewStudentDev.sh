#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}\")" && pwd)"
if [[ -f /usr/local/lib/skyview-student-dev/common.sh ]]; then
  # shellcheck source=/usr/local/lib/skyview-student-dev/common.sh
  source /usr/local/lib/skyview-student-dev/common.sh
else
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
  # common.sh enables -e; validation must collect all results instead.
  set +e
fi
set +e

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

pass() { printf 'PASS  %s\n' "$*"; PASS_COUNT=$((PASS_COUNT+1)); }
warnv() { printf 'WARN  %s\n' "$*"; WARN_COUNT=$((WARN_COUNT+1)); }
fail() { printf 'FAIL  %s\n' "$*"; FAIL_COUNT=$((FAIL_COUNT+1)); }
info() { printf 'INFO  %s\n' "$*"; }

check_command() {
  local cmd="$1" label="${2:-$1}"
  if command -v "$cmd" >/dev/null 2>&1; then
    pass "$label found: $(command -v "$cmd")"
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

TARGET_USER="$(cat "$SKYVIEW_ETC/target-user" 2>/dev/null || printf '%s' "${USER:-}")"
TARGET_HOME="$(cat "$SKYVIEW_ETC/target-home" 2>/dev/null || printf '%s' "${HOME:-}")"
[[ -n "$TARGET_HOME" ]] || TARGET_HOME="$HOME"
info "Configured student/shared user: ${TARGET_USER:-unknown} (${TARGET_HOME:-unknown})"

check_command git Git
check_command gh "GitHub CLI"
check_command node Node.js
check_command npm npm
check_command codium VSCodium
check_command dbeaver DBeaver
check_command firefox Firefox
check_command pwsh "PowerShell 7"
check_command ssh OpenSSH
check_command 7z 7-Zip
check_command python3.14 "Python 3.14"
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

if command -v node >/dev/null 2>&1; then
  NODE_VERSION="$(node --version 2>/dev/null)"
  if [[ "$NODE_VERSION" =~ ^v24\. ]]; then
    pass "Node.js is on required 24.x family ($NODE_VERSION)"
  else
    fail "Node.js must remain on 24.x; detected ${NODE_VERSION:-unknown}"
  fi
fi

if command -v python3.14 >/dev/null 2>&1; then
  PY_VERSION="$(python3.14 --version 2>&1)"
  if [[ "$PY_VERSION" =~ ^Python\ 3\.14\. ]]; then
    pass "Python is on required 3.14.x family ($PY_VERSION)"
  else
    fail "Expected Python 3.14.x; detected ${PY_VERSION:-unknown}"
  fi

  TMP_VENV="$(mktemp -d)/venv"
  if python3.14 -m venv "$TMP_VENV" >/dev/null 2>&1 && "$TMP_VENV/bin/python" -m pip --version >/dev/null 2>&1; then
    pass "Python 3.14 venv and project-local pip work"
  else
    fail "Python 3.14 could not create a venv with pip"
  fi
  rm -rf "$(dirname "$TMP_VENV")"
fi

if command -v git >/dev/null 2>&1; then
  [[ "$(git config --global --get init.defaultBranch 2>/dev/null)" == "main" ]] && pass "Git default branch is main" || fail "Git init.defaultBranch is not main"
  [[ "$(git config --global --get fetch.prune 2>/dev/null)" == "true" ]] && pass "Git fetch.prune is true" || fail "Git fetch.prune is not true"
  [[ "$(git config --global --get pull.ff 2>/dev/null)" == "only" ]] && pass "Git pull.ff is only" || fail "Git pull.ff is not only"
  GIT_NAME="$(git config --global --get user.name 2>/dev/null)"
  GIT_EMAIL="$(git config --global --get user.email 2>/dev/null)"
  if [[ -z "$GIT_NAME" && -z "$GIT_EMAIL" ]]; then
    info "Git user identity is intentionally unset"
  else
    info "Git identity is configured locally: ${GIT_NAME:-<no name>} / ${GIT_EMAIL:-<no email>}"
  fi
fi

if command -v gh >/dev/null 2>&1; then
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

CODIUM_SETTINGS="$TARGET_HOME/.config/VSCodium/User/settings.json"
if [[ -s "$CODIUM_SETTINGS" ]]; then
  pass "VSCodium settings file exists"
  if command -v jq >/dev/null 2>&1 && jq -e '."editor.formatOnSave" == true and ."editor.defaultFormatter" == "esbenp.prettier-vscode" and ."files.eol" == "\n"' "$CODIUM_SETTINGS" >/dev/null 2>&1; then
    pass "VSCodium baseline settings are present"
  else
    warnv "Could not verify all VSCodium baseline settings (file may contain JSONC or user customizations)"
  fi
else
  fail "VSCodium settings file missing: $CODIUM_SETTINGS"
fi

EXT_FILE=""
[[ -f "$SKYVIEW_SHARE/extensions.txt" ]] && EXT_FILE="$SKYVIEW_SHARE/extensions.txt"
[[ -z "$EXT_FILE" && -f "$SCRIPT_DIR/extensions.txt" ]] && EXT_FILE="$SCRIPT_DIR/extensions.txt"
if command -v codium >/dev/null 2>&1 && [[ -n "$EXT_FILE" ]]; then
  INSTALLED_EXT="$(mktemp)"
  if [[ "$(id -u)" -eq 0 && -n "$TARGET_USER" ]]; then
    runuser -u "$TARGET_USER" -- env HOME="$TARGET_HOME" codium --list-extensions > "$INSTALLED_EXT" 2>/dev/null
  else
    env HOME="$TARGET_HOME" codium --list-extensions > "$INSTALLED_EXT" 2>/dev/null
  fi
  while IFS= read -r ext; do
    [[ -z "$ext" || "$ext" =~ ^[[:space:]]*# ]] && continue
    if grep -Fxiq "$ext" "$INSTALLED_EXT"; then
      pass "VSCodium extension installed: $ext"
    else
      fail "VSCodium extension missing: $ext"
    fi
  done < "$EXT_FILE"
  rm -f "$INSTALLED_EXT"
fi

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
  while IFS=, read -r name url branch enabled; do
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
printf 'RESULT: %d PASS, %d WARN, %d FAIL\n' "$PASS_COUNT" "$WARN_COUNT" "$FAIL_COUNT"

if (( FAIL_COUNT > 0 )); then
  exit 1
fi
exit 0
