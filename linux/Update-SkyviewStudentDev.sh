#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/lib/common.sh" ]]; then
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
else
  # shellcheck source=/usr/local/lib/skyview-student-dev/common.sh
  source /usr/local/lib/skyview-student-dev/common.sh
fi

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo "$0" "$@"
fi

mkdir -p "$SKYVIEW_LOG_DIR"
LOG_FILE="$SKYVIEW_LOG_DIR/update-$(date '+%Y%m%d-%H%M%S').log"
exec > >(tee -a "$LOG_FILE") 2>&1

TARGET_USER="$(cat "$SKYVIEW_ETC/target-user" 2>/dev/null || true)"
TARGET_HOME="$(cat "$SKYVIEW_ETC/target-home" 2>/dev/null || true)"



log "$SKYVIEW_NAME updater v$SKYVIEW_VERSION"
check_supported_mint >/dev/null

event progress 10 "Checking managed package updates"
log "Refreshing APT metadata..."
apt-get update

NODE_VERSION="$(apt-cache madison nodejs | awk '$3 ~ /^24\./ {print $3; exit}')"
[[ -n "$NODE_VERSION" ]] || die "No Node.js 24.x package is available."
event progress 35 "Updating managed development packages"
log "Updating the provisioned package set without performing a full OS upgrade..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git gh "nodejs=$NODE_VERSION" codium dbeaver-ce firefox powershell \
  python3.14 python3.14-venv openssh-client p7zip-full

if dpkg-query -W -f='${Status}' google-chrome-stable 2>/dev/null | grep -q 'ok installed'; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y google-chrome-stable
fi

event progress 72 "Updating PyCharm"
install_pycharm_latest

log "Maintenance completed successfully."
