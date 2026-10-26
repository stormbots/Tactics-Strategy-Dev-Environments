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
if [[ -f /work/uat/1.2.6/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions+=(1.2.6)
fi
if [[ -f /work/uat/1.2.7/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions+=(1.2.7)
fi
if [[ -f /work/uat/1.2.8/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.7 1.2.8)
fi
if [[ -f /work/uat/1.2.9/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.8 1.2.9)
fi
if [[ -f /work/uat/1.2.10/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.9 1.2.10)
fi
if [[ -f /work/uat/1.2.11/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.10 1.2.11)
fi
if [[ -f /work/uat/1.2.12/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.11 1.2.12)
fi
if [[ -f /work/uat/1.2.13/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.12 1.2.13)
fi
if [[ -f /work/uat/1.2.14/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.13 1.2.14)
fi
if [[ -f /work/uat/1.2.15/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.14 1.2.15)
fi
if [[ -f /work/uat/1.2.16/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.15 1.2.16)
fi
if [[ -f /work/uat/1.2.17/Skyview-Dev-Setup-LinuxMint-amd64.deb ]]; then
  versions=(1.2.16 1.2.17)
fi
for version in "${versions[@]}"; do
  if [[ "$version" = "${versions[1]}" ]]; then
    printf '# legacy maintenance UAT sentinel\n' > "$legacy"
    chmod 0755 "$legacy"
    if [[ "$version" == 1.2.16 || "$version" == 1.2.17 ]]; then
      '/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust' pause
    fi
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
  if [[ "$version" = "${versions[0]}" ]]; then
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
assert json.loads((root / 'policy.json').read_text())['paused'] is False
assert json.loads((root / 'active.json').read_text())['version'] == sys.argv[1]
PY
  [[ "$(cat "$student/project.txt")" == 'student project sentinel' ]]
  [[ "$(cat "$student/.config/Code/User/settings.json")" == '{"editor.fontSize":17}' ]]
  if [[ "$version" == 1.2.16 || "$version" == 1.2.17 ]]; then
    worker='/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust'
    for verb in pause resume; do
      "$worker" "$verb"
      # Reinstall the real package through APT from both prior policy states.
      apt-get -y --no-remove --reinstall -o DPkg::Lock::Timeout=60 install "$package"
      python3 -I -c "import json; assert json.load(open('/var/lib/skyview-robotics/self-update/policy.json'))['paused'] is False"
      if [[ "$version" = "${versions[1]}" ]]; then
        [[ "$(cat "$legacy")" == '# legacy maintenance UAT sentinel' ]]
      else
        [[ ! -e "$legacy" ]]
      fi
      [[ "$(cat "$student/project.txt")" == 'student project sentinel' ]]
      [[ "$(cat "$student/.config/Code/User/settings.json")" == '{"editor.fontSize":17}' ]]
      [[ ! -e /etc/systemd/system/skyview-student-dev-update.service ]]
    done
    for verb in set-paused set-enabled; do
      runuser -u nobody -- "$worker" "$verb"
    done
    echo SDE_UAT_ENABLED_DEFAULTS_MINT_OK
  fi
  echo "PASS $version: actual Mint package, enabled engine, preserved files/baseline, no provisioning/schedule"
done
echo SDE_UAT_PAIR_MINT_OK
