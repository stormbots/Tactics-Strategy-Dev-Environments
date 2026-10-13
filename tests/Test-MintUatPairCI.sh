#!/usr/bin/env bash
# ONLY the disposable, actual Mint ISO userland built by Prepare-MintNativeCI.sh.
set -Eeuo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "$(id -u)" == 0 ]] || exit 1
source /etc/os-release
[[ "$ID" == linuxmint && "$VERSION_ID" == 22* ]] || exit 1
export DEBIAN_FRONTEND=noninteractive
apt-get update
root=/opt/sde-uat-pair
install -d -m 0700 "$root"
student=/home/sde-uat
install -d "$student/.config/Code/User"
printf 'student project sentinel\n' > "$student/project.txt"
printf '{"editor.fontSize":17}\n' > "$student/.config/Code/User/settings.json"
legacy=/usr/local/sbin/skyview-student-dev-update
versions=(1.2.2 1.2.3)
if [[ -f /work/uat/1.2.4/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions+=(1.2.4)
fi
if [[ -f /work/uat/1.2.5/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions+=(1.2.5)
fi
for version in "${versions[@]}"; do
  if [[ "$version" = 1.2.3 ]]; then
    printf '# legacy maintenance UAT sentinel\n' > "$legacy"
    chmod 0755 "$legacy"
  fi
  package="$root/installer.deb"
  cp "/work/uat/$version/Skyview-Dev-Setup-LinuxMint-amd64.deb" "$package"
  [[ "$(dpkg-deb -f "$package" Package)" == skyview-dev-setup ]]
  [[ "$(dpkg-deb -f "$package" Version)" == "$version" ]]
  [[ "$(dpkg-deb -f "$package" Architecture)" == amd64 ]]
  apt-get -y --no-remove -o DPkg::Lock::Timeout=60 install "$package"
  [[ "$(dpkg-query -W -f='${Status}' skyview-dev-setup)" == 'install ok installed' ]]
  [[ "$(dpkg-query -W -f='${Version}' skyview-dev-setup)" == "$version" ]]
  [[ -x /usr/bin/skyview-dev-setup ]]
  if [[ "$version" = 1.2.2 ]]; then
    [[ ! -e "$legacy" ]]
  else
    [[ "$(cat "$legacy")" == '# legacy maintenance UAT sentinel' ]]
    [[ "$("/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust" coordination-status)" == '"needs_repair"' ]]
  fi
  [[ ! -e /etc/systemd/system/skyview-student-dev-update.service ]]
  [[ ! -e /var/lib/skyview-robotics/student-dev/version ]]
  python3 -I - "$version" <<'PY'
import json, sys
from pathlib import Path
root = Path('/var/lib/skyview-robotics/self-update')
assert json.loads((root / 'policy.json').read_text())['paused'] is True
assert json.loads((root / 'active.json').read_text())['version'] == sys.argv[1]
PY
  [[ "$(cat "$student/project.txt")" == 'student project sentinel' ]]
  [[ "$(cat "$student/.config/Code/User/settings.json")" == '{"editor.fontSize":17}' ]]
  echo "PASS $version: actual Mint package, paused engine, preserved files/baseline, no provisioning/schedule"
done
echo SDE_UAT_PAIR_MINT_OK
