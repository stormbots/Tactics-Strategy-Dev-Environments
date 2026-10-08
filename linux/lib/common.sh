#!/usr/bin/env bash
set -Eeuo pipefail

export SKYVIEW_VERSION="1.2.1"
export SKYVIEW_NAME="Skyview Robotics Student Dev Environment"
export SKYVIEW_ETC="/etc/skyview-robotics/student-dev"
export SKYVIEW_LIB="/usr/local/lib/skyview-student-dev"
export SKYVIEW_SHARE="/usr/local/share/skyview-robotics/student-dev"
export SKYVIEW_STATE="/var/lib/skyview-robotics/student-dev"
export SKYVIEW_LOG_DIR="/var/log/skyview-robotics/student-dev"
PYCHARM_API='https://data.services.jetbrains.com/products/releases?code=PCP&latest=true&type=release'

# Stable protocol: type, key/percentage, and escaped one-line description.
event() { printf 'SKYVIEW_EVENT|%s|%s|%s\n' "$1" "$2" "${3//$'\n'/ }"; }
log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
warn() { event warning provisioning "$*" >&2; printf '[%s] WARNING: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; }
die() { event error provisioning "$*" >&2; printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

ubuntu_base_version() {
  . /etc/os-release
  local code="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
  case "$code" in
    noble) printf '24.04\n' ;;
    jammy) printf '22.04\n' ;;
    resolute) printf '26.04\n' ;;
    *) return 1 ;;
  esac
}

check_supported_mint() {
  . /etc/os-release
  [[ "${ID:-}" == "linuxmint" ]] || die "This package supports Linux Mint only. Detected: ${PRETTY_NAME:-unknown}."
  case "${VERSION_ID:-}" in
    21|21.*|22|22.*) ;;
    *) warn "Linux Mint ${VERSION_ID:-unknown} has not been validated with this package; continuing because its Ubuntu base may still be compatible." ;;
  esac
  local base
  base="$(ubuntu_base_version)" || die "Unsupported/unknown Ubuntu package base: ${UBUNTU_CODENAME:-${VERSION_CODENAME:-unknown}}"
  printf '%s\n' "$base"
}

install_pycharm_latest() {
  require_cmd curl
  require_cmd jq
  require_cmd sha256sum
  require_cmd tar

  local arch key json version link checksum_link expected tmpdir archive actual install_dir current_target
  arch="$(dpkg --print-architecture)"
  case "$arch" in
    amd64) key='linux' ;;
    arm64) key='linuxARM64' ;;
    *) die "PyCharm automated install supports amd64 and arm64 only; detected $arch." ;;
  esac

  json="$(curl -fsSL "$PYCHARM_API")"
  version="$(jq -r '.PCP[0].version // empty' <<<"$json")"
  link="$(jq -r --arg k "$key" '.PCP[0].downloads[$k].link // empty' <<<"$json")"
  checksum_link="$(jq -r --arg k "$key" '.PCP[0].downloads[$k].checksumLink // empty' <<<"$json")"
  [[ -n "$version" && -n "$link" && -n "$checksum_link" ]] || die "Unable to resolve the latest PyCharm release from JetBrains."

  install_dir="/opt/pycharm-${version}"
  current_target="$(readlink -f /opt/pycharm 2>/dev/null || true)"
  if [[ -d "$install_dir" && "$current_target" == "$install_dir" ]]; then
    log "PyCharm ${version} is already current."
    return 0
  fi

  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' RETURN
  archive="$tmpdir/pycharm.tar.gz"
  log "Downloading PyCharm ${version} from JetBrains..."
  curl -fL --retry 3 --retry-delay 2 -o "$archive" "$link"
  expected="$(curl -fsSL "$checksum_link" | awk '{print $1}' | head -n1)"
  [[ "$expected" =~ ^[0-9a-fA-F]{64}$ ]] || die "Could not obtain a valid PyCharm SHA-256 checksum."
  actual="$(sha256sum "$archive" | awk '{print $1}')"
  [[ "${actual,,}" == "${expected,,}" ]] || die "PyCharm checksum verification failed."

  [[ ! -e "$install_dir" ]] || die "Existing PyCharm directory is incomplete; mentor review required: $install_dir"
  mkdir -p "$install_dir"
  tar -xzf "$archive" -C "$install_dir" --strip-components=1
  [[ -x "$install_dir/bin/pycharm" ]] || die "PyCharm archive did not contain the expected launcher."

  ln -sfn "$install_dir" /opt/pycharm
  ln -sfn /opt/pycharm/bin/pycharm /usr/local/bin/pycharm

  cat > /usr/share/applications/pycharm.desktop <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=PyCharm
Comment=Python IDE
Exec=/opt/pycharm/bin/pycharm %f
Icon=/opt/pycharm/bin/pycharm.svg
Terminal=false
Categories=Development;IDE;
StartupWMClass=jetbrains-pycharm
DESKTOP

  log "Installed PyCharm ${version}."
  rm -rf "$tmpdir"
  trap - RETURN
}

install_codium_extensions_for_user() {
  local user="$1" home="$2" ext_file="$3" ext
  [[ -f "$ext_file" ]] || die "Extension list not found: $ext_file"
  command -v codium >/dev/null 2>&1 || die "VSCodium CLI (codium) is not installed."
  while IFS= read -r ext; do
    [[ -z "$ext" || "$ext" =~ ^[[:space:]]*# ]] && continue
    log "Ensuring VSCodium extension for ${user}: ${ext}"
    if [[ "$(id -u)" -eq 0 ]]; then
      runuser -u "$user" -- env HOME="$home" codium --install-extension "$ext" --force >/dev/null
    else
      env HOME="$home" codium --install-extension "$ext" --force >/dev/null
    fi
  done < "$ext_file"
}
