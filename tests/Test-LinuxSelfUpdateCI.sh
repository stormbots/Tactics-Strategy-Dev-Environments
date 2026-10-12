#!/usr/bin/env bash
# ONLY disposable Linux Mint container filesystem; never a student workstation.
set -Eeuo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "$(id -u)" == 0 ]] || exit 1
source /etc/os-release
[[ "$ID" == linuxmint && "$VERSION_ID" == 22* ]] || { echo 'Actual supported Mint required'; exit 1; }
printf 'Native evidence: %s; kernel/container desktop UAT remains separate\n' "$PRETTY_NAME"
export DEBIAN_FRONTEND=noninteractive
apt-get update
root=/opt/sde-fixtures
# Export only test/native output, never fixture keys or protected staging files.
trap 'if [[ -d /evidence && -f "$root/native-result.txt" ]]; then cp "$root/native-result.txt" /evidence/mint-native.txt; fi' EXIT
install -d -m 0700 "$root/1.2.2/failure"
cp /work/dist/Skyview-Dev-Setup-LinuxMint-amd64.deb "$root/old.deb"
cp /work/installer/src-tauri/target/release/bundle/deb/*1.2.2*.deb "$root/1.2.2/Skyview-Dev-Setup-LinuxMint-amd64.deb"
printf 'test placeholder\n' > "$root/1.2.2/Skyview-Dev-Setup-Windows-x64.exe"
printf 'test placeholder\n' > "$root/1.2.2/failure/Skyview-Dev-Setup-Windows-x64.exe"
cp /work/updater/target/debug/sde-native-mint-tests "$root/native-tests"
chmod 0700 "$root/native-tests"
apt-get -y --no-remove install "$root/old.deb"
[[ ! -e /usr/local/sbin/skyview-student-dev-update ]]
[[ ! -e /etc/systemd/system/skyview-student-dev-update.service ]]
[[ ! -e /var/lib/skyview-robotics/student-dev/version ]]
python3 -I -c "import json; assert json.load(open('/var/lib/skyview-robotics/self-update/policy.json')) == dict(schemaVersion=1,paused=True)"
# Repeat packaging activation to exercise existing receipt replacement.
python3 -I '/usr/lib/Skyview Dev Setup/backend/linux/self-update/bootstrap.py'
install -d -m 0755 /usr/local/lib/skyview-student-dev /home/sde-student /var/lib/skyview-robotics/student-dev
for name in common.sh tool_records.py coordination.sh coordination.py; do
  install -m 0644 "/work/linux/lib/$name" "/usr/local/lib/skyview-student-dev/$name"
done
# Deterministic applied tool policy; no dev-package provisioning in this fixture.
cat > /usr/local/sbin/skyview-student-dev-update <<'EOF'
#!/bin/bash
# SDE_COORDINATION_V1
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/coordination.sh"
skyview_coordinate system "$@"
[[ "$SCRIPT_DIR" == /var/lib/skyview-robotics/self-update/runs/*/applied-baseline ]]
for name in common.sh tool_records.py coordination.sh coordination.py; do
  cmp "$SCRIPT_DIR/lib/$name" "/usr/local/lib/skyview-student-dev/$name"
done
printf 'Applied policy snapshot used with held coordination descriptors\n'
EOF
chmod 0755 /usr/local/sbin/skyview-student-dev-update
printf '1.2.1\n' > /var/lib/skyview-robotics/student-dev/version
printf 'student home/project sentinel\n' > /home/sde-student/project.txt
install -d -m 0755 /etc/systemd/system
cp /work/linux/systemd/skyview-student-dev-update.service /etc/systemd/system/
printf '[Unit]\nDescription=Custom disabled schedule\n[Timer]\nOnCalendar=Fri *-*-* 04:35:00\nPersistent=true\n' > /etc/systemd/system/skyview-student-dev-update.timer
# Signed test-only real package failure, leaves DPKG state for mentor review.
install -d -m 0755 "$root/failure-build/DEBIAN"
printf 'Package: skyview-dev-setup\nVersion: 1.2.3\nArchitecture: amd64\nMaintainer: Disposable CI <ci@example.invalid>\nDescription: deterministic native failure fixture\n' > "$root/failure-build/DEBIAN/control"
printf '#!/bin/sh\nexit 23\n' > "$root/failure-build/DEBIAN/postinst"
chmod 0755 "$root/failure-build/DEBIAN/postinst"
dpkg-deb --build "$root/failure-build" "$root/1.2.2/failure/Skyview-Dev-Setup-LinuxMint-amd64.deb"
SDE_MINT_NATIVE_FIXTURE="$root/1.2.2/Skyview-Dev-Setup-LinuxMint-amd64.deb" "$root/native-tests" --exact linux_install::tests::signed_upgrade_on_native_mint --nocapture | tee "$root/native-result.txt"
grep -q SDE_NATIVE_MINT_UPGRADE_OK "$root/native-result.txt"
grep -q SDE_E2E_NATIVE_MINT_OK "$root/native-result.txt"
