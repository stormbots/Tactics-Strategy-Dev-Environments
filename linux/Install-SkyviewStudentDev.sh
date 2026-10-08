#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

SYSTEM_ONLY=0
[[ "${1:-}" == "--system-only" ]] && SYSTEM_ONLY=1
if [[ "$(id -u)" -eq 0 && "$SYSTEM_ONLY" != 1 ]]; then
  die "Run this installer as the student/shared desktop user, not with sudo. The script will request sudo when needed."
fi

TARGET_USER="$(id -un)"
TARGET_HOME="$HOME"
if [[ "$SYSTEM_ONLY" == 1 ]]; then
  [[ "$(id -u)" -eq 0 ]] || die "System provisioning requires administrative privileges."
  sudo() { "$@"; }
else
  sudo -v
fi
event progress 5 "Checking system"
trap 'event error provisioning "System setup failed at line $LINENO. See details for the package error."' ERR
MINT_BASE="$(check_supported_mint)"
ARCH="$(dpkg --print-architecture)"
case "$ARCH" in
  amd64|arm64) ;;
  *) die "Unsupported architecture: $ARCH" ;;
esac

sudo mkdir -p "$SKYVIEW_LOG_DIR"
sudo chown root:adm "$SKYVIEW_LOG_DIR"
LOG_FILE="$SKYVIEW_LOG_DIR/install-$(date '+%Y%m%d-%H%M%S').log"
exec > >(sudo tee -a "$LOG_FILE") 2>&1

log "$SKYVIEW_NAME installer v$SKYVIEW_VERSION"
log "Target user: $TARGET_USER ($TARGET_HOME)"
log "Detected Linux Mint Ubuntu base: $MINT_BASE; architecture: $ARCH"

if [[ "$SYSTEM_ONLY" != 1 && "${XDG_CURRENT_DESKTOP:-}" != *Cinnamon* && "${DESKTOP_SESSION:-}" != *cinnamon* ]]; then
  warn "Cinnamon was not detected in the current session. The package is designed for Linux Mint Cinnamon but will continue."
fi

event progress 10 "Installing prerequisites"
log "Installing base prerequisites..."
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl wget gnupg jq software-properties-common apt-transport-https \
  git openssh-client p7zip-full unzip tar xz-utils desktop-file-utils \
  libxi6 libxrender1 libxtst6 mesa-utils libfontconfig1 libgtk-3-bin dbus-user-session libxcb-keysyms1

event progress 20 "Configuring trusted package sources"
log "Configuring GitHub CLI official APT repository..."
sudo install -d -m 0755 /etc/apt/keyrings
TMP_KEY="$(mktemp)"
wget -qO "$TMP_KEY" https://cli.github.com/packages/githubcli-archive-keyring.gpg
sudo install -m 0644 "$TMP_KEY" /etc/apt/keyrings/githubcli-archive-keyring.gpg
rm -f "$TMP_KEY"
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\n' "$ARCH" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null

log "Configuring VSCodium APT repository..."
wget -qO - https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg \
  | gpg --dearmor \
  | sudo tee /usr/share/keyrings/vscodium-archive-keyring.gpg >/dev/null
sudo chmod 0644 /usr/share/keyrings/vscodium-archive-keyring.gpg
sudo tee /etc/apt/sources.list.d/vscodium.sources >/dev/null <<EOF_VSCODIUM
Types: deb
URIs: https://download.vscodium.com/debs
Suites: vscodium
Components: main
Architectures: amd64 arm64
Signed-by: /usr/share/keyrings/vscodium-archive-keyring.gpg
EOF_VSCODIUM

log "Configuring DBeaver Community APT repository..."
wget -qO - https://dbeaver.io/debs/dbeaver.gpg.key \
  | gpg --dearmor \
  | sudo tee /usr/share/keyrings/dbeaver.gpg.key >/dev/null
sudo chmod 0644 /usr/share/keyrings/dbeaver.gpg.key
printf 'deb [signed-by=/usr/share/keyrings/dbeaver.gpg.key] https://dbeaver.io/debs/dbeaver-ce /\n' \
  | sudo tee /etc/apt/sources.list.d/dbeaver.list >/dev/null

log "Configuring Microsoft package repository for PowerShell..."
TMP_DIR="$(mktemp -d)"
wget -q -O "$TMP_DIR/packages-microsoft-prod.deb" "https://packages.microsoft.com/config/ubuntu/${MINT_BASE}/packages-microsoft-prod.deb"
sudo dpkg -i "$TMP_DIR/packages-microsoft-prod.deb"
rm -rf "$TMP_DIR"

log "Configuring NodeSource Node.js 24.x repository..."
TMP_NODE="$(mktemp)"
curl -fsSL https://deb.nodesource.com/setup_24.x -o "$TMP_NODE"
sudo bash "$TMP_NODE"
rm -f "$TMP_NODE"

log "Configuring Python 3.14 repository (Deadsnakes PPA)..."
sudo add-apt-repository -y ppa:deadsnakes/ppa

event progress 40 "Installing development applications"
# Enforce the runtime family even if another repository offers a newer major.
sudo apt-get update
# Consume the full listing so apt-cache cannot hit SIGPIPE under pipefail.
NODE_VERSION="$(apt-cache madison nodejs | awk '$3 ~ /^24\./ && !found {print $3; found=1}')"
[[ -n "$NODE_VERSION" ]] || die "No Node.js 24.x package is available from configured sources."
log "Installing development applications..."
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  gh "nodejs=$NODE_VERSION" codium dbeaver-ce firefox powershell \
  python3.14 python3.14-venv

if command -v google-chrome >/dev/null 2>&1 || command -v google-chrome-stable >/dev/null 2>&1; then
  log "Google Chrome is already installed."
else
  if [[ "$ARCH" != "amd64" ]]; then
    warn "Automated Google Chrome installation is currently packaged for amd64 only; skipping Chrome on $ARCH."
  else
    log "Installing Google Chrome stable..."
    CHROME_DEB="$(mktemp --suffix=.deb)"
    curl -fL --retry 3 -o "$CHROME_DEB" https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt-get install -y "$CHROME_DEB"
    rm -f "$CHROME_DEB"
  fi
fi

event progress 72 "Installing PyCharm with checksum verification"
log "Installing/updating PyCharm from JetBrains..."
sudo bash -c "source '$SCRIPT_DIR/lib/common.sh'; install_pycharm_latest"

if [[ "$SYSTEM_ONLY" != 1 ]]; then
  bash "$SCRIPT_DIR/Configure-SkyviewUser.sh"
fi

log "Installing persistent Skyview maintenance files..."
sudo install -d -m 0755 "$SKYVIEW_ETC" "$SKYVIEW_LIB" "$SKYVIEW_SHARE" "$SKYVIEW_STATE"
sudo install -m 0644 "$SCRIPT_DIR/lib/common.sh" "$SKYVIEW_LIB/common.sh"
sudo install -m 0644 "$SCRIPT_DIR/lib/tool_records.py" "$SKYVIEW_LIB/tool_records.py"
sudo install -m 0644 "$SCRIPT_DIR/extensions.txt" "$SKYVIEW_SHARE/extensions.txt"
sudo install -m 0644 "$SCRIPT_DIR/config/codium-settings.json" "$SKYVIEW_SHARE/codium-settings.json"
if [[ ! -f "$SKYVIEW_ETC/repositories.csv" ]]; then
  sudo install -m 0644 "$SCRIPT_DIR/repositories.csv" "$SKYVIEW_ETC/repositories.csv"
fi
if [[ "$SYSTEM_ONLY" != 1 ]]; then
  printf '%s\n' "$TARGET_USER" | sudo tee "$SKYVIEW_ETC/target-user" >/dev/null
  printf '%s\n' "$TARGET_HOME" | sudo tee "$SKYVIEW_ETC/target-home" >/dev/null
fi
printf '%s\n' "$SKYVIEW_VERSION" | sudo tee "$SKYVIEW_STATE/version" >/dev/null

sudo install -m 0755 "$SCRIPT_DIR/Update-SkyviewStudentDev.sh" /usr/local/sbin/skyview-student-dev-update
sudo install -m 0755 "$SCRIPT_DIR/Validate-SkyviewStudentDev.sh" /usr/local/sbin/skyview-student-dev-validate

event progress 78 "Configuring weekly maintenance"
log "Installing weekly maintenance timer..."
sudo install -m 0644 "$SCRIPT_DIR/systemd/skyview-student-dev-update.service" /etc/systemd/system/skyview-student-dev-update.service
sudo install -m 0644 "$SCRIPT_DIR/systemd/skyview-student-dev-update.timer" /etc/systemd/system/skyview-student-dev-update.timer
sudo systemctl daemon-reload
sudo systemctl enable --now skyview-student-dev-update.timer

[[ "$SYSTEM_ONLY" == 1 ]] && exit 0
event progress 95 "Validating environment"
log "Running validation..."
if bash "$SCRIPT_DIR/Validate-SkyviewStudentDev.sh"; then
  log "Installation and validation completed successfully."
else
  warn "Installation completed, but validation reported one or more failures. Review the output above and $LOG_FILE."
  exit 2
fi
