#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"
[[ "$(id -u)" -ne 0 ]] || die "User configuration must not run as root."
TARGET_USER="$(id -un)"
TARGET_HOME="$HOME"
event progress 82 "Configuring your development workspace"
log "Creating development workspace..."
mkdir -p "$TARGET_HOME/Development"

log "Applying Git defaults (identity intentionally left unset)..."
git config --global init.defaultBranch main
git config --global fetch.prune true
git config --global pull.ff only

log "Applying baseline VSCodium settings..."
CODIUM_DIR="$TARGET_HOME/.config/VSCodium/User"
CODIUM_SETTINGS="$CODIUM_DIR/settings.json"
mkdir -p "$CODIUM_DIR"
if [[ ! -s "$CODIUM_SETTINGS" ]]; then
  install -m 0644 "$SCRIPT_DIR/config/codium-settings.json" "$CODIUM_SETTINGS"
else
  MERGED="$(mktemp)"
  if jq -s '.[1] * .[0]' "$CODIUM_SETTINGS" "$SCRIPT_DIR/config/codium-settings.json" > "$MERGED" 2>/dev/null; then
    cp "$CODIUM_SETTINGS" "$CODIUM_SETTINGS.pre-skyview-v${SKYVIEW_VERSION}.bak"
    install -m 0644 "$MERGED" "$CODIUM_SETTINGS"
  else
    warn "Existing VSCodium settings.json is not strict JSON (likely JSONC); it was preserved unchanged. Baseline settings are in config/codium-settings.json."
  fi
  rm -f "$MERGED"
fi

install_codium_extensions_for_user "$TARGET_USER" "$TARGET_HOME" "$SCRIPT_DIR/extensions.txt"

log "Provisioning optional repositories from repositories.csv..."
REPO_FILE="$SKYVIEW_ETC/repositories.csv"
[[ -f "$REPO_FILE" ]] || REPO_FILE="$SCRIPT_DIR/repositories.csv"
if [[ -f "$REPO_FILE" ]]; then
  tail -n +2 "$REPO_FILE" | while IFS=, read -r name url branch enabled; do
    name="${name//\r/}"; url="${url//\r/}"; branch="${branch//\r/}"; enabled="${enabled//\r/}"
    [[ -z "$name" || -z "$url" ]] && continue
    case "${enabled,,}" in
      1|true|yes|y)
        [[ "$name" =~ ^[a-zA-Z0-9_-][a-zA-Z0-9._-]*$ && "$name" != ".." ]] || die "Invalid repository folder: $name"
        [[ "$url" == https://* || "$url" == git@* ]] || die "Unsupported repository URL for $name"
        dest="$TARGET_HOME/Development/$name"
        if [[ -d "$dest/.git" ]]; then
          log "Repository already present: $name"
        elif [[ -e "$dest" ]]; then
          warn "Skipping repository $name because $dest exists but is not a Git repository."
        else
          if [[ -n "$branch" ]]; then
            GIT_TERMINAL_PROMPT=0 git clone --branch "$branch" -- "$url" "$dest"
          else
            GIT_TERMINAL_PROMPT=0 git clone -- "$url" "$dest"
          fi
        fi
        ;;
    esac
  done
fi

event progress 94 "User configuration complete"
