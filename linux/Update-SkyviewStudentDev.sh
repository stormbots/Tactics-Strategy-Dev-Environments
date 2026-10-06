#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f /usr/local/lib/skyview-student-dev/common.sh ]]; then
  # shellcheck source=/usr/local/lib/skyview-student-dev/common.sh
  source /usr/local/lib/skyview-student-dev/common.sh
else
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo "$0" "$@"
fi

mkdir -p "$SKYVIEW_LOG_DIR"
LOG_FILE="$SKYVIEW_LOG_DIR/update-$(date '+%Y%m%d-%H%M%S').log"
exec > >(tee -a "$LOG_FILE") 2>&1

TARGET_USER="$(cat "$SKYVIEW_ETC/target-user" 2>/dev/null || true)"
TARGET_HOME="$(cat "$SKYVIEW_ETC/target-home" 2>/dev/null || true)"
[[ -n "$TARGET_USER" && -n "$TARGET_HOME" ]] || die "Skyview target user metadata is missing. Re-run the installer."
id "$TARGET_USER" >/dev/null 2>&1 || die "Configured target user does not exist: $TARGET_USER"

log "$SKYVIEW_NAME updater v$SKYVIEW_VERSION"
check_supported_mint >/dev/null

log "Refreshing APT metadata..."
apt-get update

log "Updating the provisioned package set without performing a full OS upgrade..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git gh nodejs codium dbeaver-ce firefox powershell \
  python3.14 python3.14-venv openssh-client p7zip-full

if dpkg-query -W -f='${Status}' google-chrome-stable 2>/dev/null | grep -q 'ok installed'; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y google-chrome-stable
fi

install_pycharm_latest

if [[ -f "$SKYVIEW_SHARE/extensions.txt" ]] && command -v codium >/dev/null 2>&1; then
  install_codium_extensions_for_user "$TARGET_USER" "$TARGET_HOME" "$SKYVIEW_SHARE/extensions.txt"
fi

log "Maintenance completed successfully."
