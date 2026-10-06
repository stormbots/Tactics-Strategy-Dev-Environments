#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

if [[ "$(id -u)" -eq 0 ]]; then
  die "Run this installer as the student/shared desktop user, not with sudo. The script will request sudo when needed."
fi

TARGET_USER="${USER}"
TARGET_HOME="${HOME}"
sudo -v
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

if [[ "${XDG_CURRENT_DESKTOP:-}" != *Cinnamon* && "${DESKTOP_SESSION:-}" != *cinnamon* ]]; then
  warn "Cinnamon was not detected in the current session. The package is designed for Linux Mint Cinnamon but will continue."
fi

log "Installing base prerequisites..."
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl wget gnupg jq software-properties-common apt-transport-https \
  git openssh-client p7zip-full unzip tar xz-utils desktop-file-utils \
  libxi6 libxrender1 libxtst6 mesa-utils libfontconfig1 libgtk-3-bin dbus-user-session libxcb-keysyms1

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
sudo -E bash "$TMP_NODE"
rm -f "$TMP_NODE"

log "Configuring Python 3.14 repository (Deadsnakes PPA)..."
sudo add-apt-repository -y ppa:deadsnakes/ppa

log "Installing development applications..."
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  gh nodejs codium dbeaver-ce firefox powershell \
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

log "Installing/updating PyCharm from JetBrains..."
sudo bash -c "source '$SCRIPT_DIR/lib/common.sh'; install_pycharm_latest"

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
  if jq -s '.[0] * .[1]' "$CODIUM_SETTINGS" "$SCRIPT_DIR/config/codium-settings.json" > "$MERGED" 2>/dev/null; then
    cp "$CODIUM_SETTINGS" "$CODIUM_SETTINGS.pre-skyview-v${SKYVIEW_VERSION}.bak"
    install -m 0644 "$MERGED" "$CODIUM_SETTINGS"
  else
    warn "Existing VSCodium settings.json is not strict JSON (likely JSONC); it was preserved unchanged. Baseline settings are in config/codium-settings.json."
  fi
  rm -f "$MERGED"
fi

install_codium_extensions_for_user "$TARGET_USER" "$TARGET_HOME" "$SCRIPT_DIR/extensions.txt"

log "Provisioning optional repositories from repositories.csv..."
REPO_FILE="$SCRIPT_DIR/repositories.csv"
if [[ -f "$REPO_FILE" ]]; then
  tail -n +2 "$REPO_FILE" | while IFS=, read -r name url branch enabled; do
    name="${name//\r/}"; url="${url//\r/}"; branch="${branch//\r/}"; enabled="${enabled//\r/}"
    [[ -z "$name" || -z "$url" ]] && continue
    case "${enabled,,}" in
      1|true|yes|y)
        dest="$TARGET_HOME/Development/$name"
        if [[ -d "$dest/.git" ]]; then
          log "Repository already present: $name"
        elif [[ -e "$dest" ]]; then
          warn "Skipping repository $name because $dest exists but is not a Git repository."
        else
          if [[ -n "$branch" ]]; then
            git clone --branch "$branch" "$url" "$dest"
          else
            git clone "$url" "$dest"
          fi
        fi
        ;;
    esac
  done
fi

log "Installing persistent Skyview maintenance files..."
sudo install -d -m 0755 "$SKYVIEW_ETC" "$SKYVIEW_LIB" "$SKYVIEW_SHARE" "$SKYVIEW_STATE"
sudo install -m 0644 "$SCRIPT_DIR/lib/common.sh" "$SKYVIEW_LIB/common.sh"
sudo install -m 0644 "$SCRIPT_DIR/extensions.txt" "$SKYVIEW_SHARE/extensions.txt"
sudo install -m 0644 "$SCRIPT_DIR/config/codium-settings.json" "$SKYVIEW_SHARE/codium-settings.json"
sudo install -m 0644 "$SCRIPT_DIR/repositories.csv" "$SKYVIEW_ETC/repositories.csv"
printf '%s\n' "$TARGET_USER" | sudo tee "$SKYVIEW_ETC/target-user" >/dev/null
printf '%s\n' "$TARGET_HOME" | sudo tee "$SKYVIEW_ETC/target-home" >/dev/null
printf '%s\n' "$SKYVIEW_VERSION" | sudo tee "$SKYVIEW_STATE/version" >/dev/null
sudo chmod 0644 "$SKYVIEW_ETC/target-user" "$SKYVIEW_ETC/target-home" "$SKYVIEW_ETC/repositories.csv" "$SKYVIEW_STATE/version"

sudo install -m 0755 "$SCRIPT_DIR/Update-SkyviewStudentDev.sh" /usr/local/sbin/skyview-student-dev-update
sudo install -m 0755 "$SCRIPT_DIR/Validate-SkyviewStudentDev.sh" /usr/local/sbin/skyview-student-dev-validate

log "Installing weekly maintenance timer..."
sudo install -m 0644 "$SCRIPT_DIR/systemd/skyview-student-dev-update.service" /etc/systemd/system/skyview-student-dev-update.service
sudo install -m 0644 "$SCRIPT_DIR/systemd/skyview-student-dev-update.timer" /etc/systemd/system/skyview-student-dev-update.timer
sudo systemctl daemon-reload
sudo systemctl enable --now skyview-student-dev-update.timer

log "Running validation..."
if sudo -u "$TARGET_USER" env HOME="$TARGET_HOME" /usr/local/sbin/skyview-student-dev-validate; then
  log "Installation and validation completed successfully."
else
  warn "Installation completed, but validation reported one or more failures. Review the output above and $LOG_FILE."
  exit 2
fi
