#!/usr/bin/env bash
# Destructive installation probe: run ONLY on a disposable CI runner.
set -Eeuo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "$(id -u)" == 0 ]] || { echo 'Root on disposable Actions runner required'; exit 1; }
root="$1"
echo "Evidence environment: $(. /etc/os-release; echo "$PRETTY_NAME")"
maintenance=/usr/local/sbin/skyview-student-dev-update
[[ ! -e "$maintenance" ]] || { echo 'Runner already provisioned'; exit 1; }
sentinel="$root/student.txt"
printf 'student preservation sentinel\n' > "$sentinel"
export DEBIAN_FRONTEND=noninteractive
apt-get update
for version in 1.2.0 1.2.1; do
  deb="$root/$version/Skyview-Dev-Setup-LinuxMint-amd64.deb"
  [[ "$(dpkg-deb -f "$deb" Package)" == skyview-dev-setup ]]
  [[ "$(dpkg-deb -f "$deb" Version)" == "$version" ]]
  [[ "$(dpkg-deb -f "$deb" Architecture)" == amd64 ]]
  echo "DEB $version metadata verified"
  control="$root/control-$version"
  mkdir -p "$control"
  dpkg-deb --control "$deb" "$control"
  find "$control" -maxdepth 1 -type f -print
  for hook in preinst postinst prerm postrm; do
    if [[ -f "$control/$hook" ]]; then cat "$control/$hook"; fi
  done
  apt-get -y -o DPkg::Lock::Timeout=60 --no-remove install "$deb"
  [[ "$(dpkg-query -W -f='${Version}' skyview-dev-setup)" == "$version" ]]
  [[ "$(dpkg-query -W -f='${Status}' skyview-dev-setup)" == 'install ok installed' ]]
  [[ -x /usr/bin/skyview-dev-setup ]]
  [[ -f '/usr/lib/Skyview Dev Setup/backend/linux/Update-SkyviewStudentDev.sh' ]]
  [[ ! -e "$maintenance" ]]
  ! pgrep -x skyview-dev-setup
  [[ "$(cat "$sentinel")" == 'student preservation sentinel' ]]
  echo "PASS $version: package configured, resources, no provisioning, no GUI launch, student marker"
done
