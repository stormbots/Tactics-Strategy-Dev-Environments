#!/bin/bash
# Linux Mint: bash /path/to/Start-SDE-Maintenance-Linux.sh
set -Eeuo pipefail
if (( EUID != 0 )); then
    exec /usr/bin/sudo /bin/bash -- "$(/usr/bin/readlink -f -- "${BASH_SOURCE[0]}")"
fi
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
umask 077
worker='/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust'
service=skyview-student-dev-update.service
timer=skyview-student-dev-update.timer
log=$(/usr/bin/mktemp /var/tmp/SDE-maintenance-launch.XXXXXX.log)
exec > >(/usr/bin/tee -a "$log") 2>&1
finish() {
    result=$?
    if (( result != 0 )); then
        printf '\nFAILED (exit %s). Earlier successful changes may remain enabled.\nDo not assume maintenance started.\n' "$result"
    fi
    printf '\nLocal launcher log: %s\n' "$log"
    if [[ -t 0 ]]; then read -r -p 'Press Enter to close...' _ || true; fi
    exit "$result"
}
trap finish EXIT
source /etc/os-release
[[ "${ID:-}" == linuxmint ]] || { echo 'This launcher requires Linux Mint.'; exit 1; }
[[ -x "$worker" ]] || { echo 'Installed SDE updater missing. Install the authenticated stable package first.'; exit 1; }
for unit in "$service" "$timer"; do
    [[ "$(/usr/bin/systemctl show "$unit" --property=LoadState --value)" == loaded ]] || {
        echo "Existing unit unavailable: $unit. Mentor review required; no schedule was created."
        exit 1
    }
done
[[ "$(/usr/bin/systemctl show "$service" --property=ExecStart --value)" == *'/usr/local/libexec/skyview-self-update.py'* ]] || {
    echo 'Maintenance service does not use the installed SDE updater. Mentor review required.'; exit 1;
}
echo "Computer: $(/usr/bin/hostname)"
echo 'Close SDE normally. Keep the laptop powered and online.'
echo 'Enabling automatic SDE app updates (future stable releases included)...'
"$worker" resume
status=$("$worker" self-update-status)
/usr/bin/python3 -c 'import json,sys; s=json.load(sys.stdin); sys.exit(0 if s.get("paused") is False else 1)' <<< "$status"
# Enabling the existing timer preserves its schedule. Do not create or rewrite units.
/usr/bin/systemctl enable "$timer"
/usr/bin/systemctl start "$timer"
# An already-active oneshot service is not restarted. A timer-triggered concurrent
# start coalesces with this request; systemd never runs two copies of this service.
/usr/bin/systemctl start --no-block "$service"
echo 'Automatic app updates and the existing maintenance timer are enabled.'
echo 'Maintenance start requested (or the existing active run continues).'
echo 'This is a launch confirmation, not proof the update finished.'
echo 'When maintenance finishes, reopen SDE: check About and Schedule.'
echo 'Today the target is 1.2.9; future runs select the highest eligible stable release.'
echo 'You may remove the flash drive after closing this launcher.'
