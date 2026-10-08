"""Read-only inspection of the fixed system timer and its service."""
import datetime
import json
import os
import re
import subprocess
from pathlib import Path

TIMER = "skyview-student-dev-update.timer"
SERVICE = "skyview-student-dev-update.service"
LOG_FOLDER = "/var/log/skyview-robotics/student-dev"

def show(unit):
    p = subprocess.run(["/usr/bin/systemctl", "show", unit, "--no-pager"],
                       capture_output=True, text=True, timeout=10, check=False,
                       env={**os.environ, "LC_ALL": "C", "TZ": "UTC"})
    if p.returncode:
        raise OSError("System service information could not be read.")
    return dict(line.split("=", 1) for line in p.stdout.splitlines() if "=" in line)

def timestamp(value):
    if not value or value == "n/a":
        return None
    try:
        # systemctl show renders timestamps using LC_ALL=C and TZ=UTC above.
        return datetime.datetime.strptime(value, "%a %Y-%m-%d %H:%M:%S UTC").replace(tzinfo=datetime.timezone.utc).isoformat()
    except ValueError:
        return None

def inspect():
    r = dict(status="unavailable", active=False, identifier=TIMER, frequency="Unavailable",
             nextRun=None, lastRun=None, lastResult="unavailable", resultDetail="Unavailable",
             catchUp=None, logFolder=LOG_FOLDER, logsAvailable=Path(LOG_FOLDER).is_dir(), note="")
    try:
        timer = show(TIMER)
        if timer.get("LoadState") == "not-found":
            return {**r, "status": "missing", "note": "Weekly maintenance is not installed. Use Install or Repair on Overview."}
        if timer.get("LoadState") != "loaded":
            raise OSError("The maintenance timer could not be loaded.")
        enabled = timer.get("UnitFileState") in ("enabled", "enabled-runtime")
        active = timer.get("ActiveState") == "active"
        calendars = re.findall(r"OnCalendar=(.*?) ;", timer.get("TimersCalendar", ""))
        frequency = "; ".join(calendars) or "No calendar trigger"
        delay = timer.get("RandomizedDelayUSec", "0")
        if delay not in ("0", "0us", ""):
            frequency += f"; randomized delay up to {delay}"
        r.update(status="enabled" if enabled else "disabled", active=active,
                 frequency=frequency + " (system local time unless the calendar specifies a zone)",
                 nextRun=timestamp(timer.get("NextElapseUSecRealtime")) if active else None,
                 catchUp={"yes": True, "no": False}.get(timer.get("Persistent")),
                 note="" if active else "The timer is inactive. Use Repair on Overview to restore weekly maintenance.")
        # Inspect only the owned service. Do not accept a service name from UI.
        service = show(SERVICE)
        if service.get("LoadState") != "loaded":
            r["note"] = "Maintenance service information is unavailable. Use Repair on Overview."
            return r
        raw_last = service.get("ExecMainStartTimestamp", "")
        last = timestamp(raw_last)
        r["lastRun"] = last
        if service.get("ActiveState") in ("active", "activating"):
            r.update(lastResult="running", resultDetail="Maintenance is running.")
        elif not raw_last or raw_last == "n/a":
            # A persistent timer can retain a trigger from a previous boot while
            # the service's execution result has been discarded by systemd.
            triggered = timestamp(timer.get("LastTriggerUSec"))
            r.update(lastRun=triggered, lastResult="unavailable" if triggered else "never",
                     resultDetail="Result unavailable after restart; review maintenance logs." if triggered else "This service has never run in the available history.")
        elif not last:
            r["resultDetail"] = "Last run timestamp is unavailable."
        else:
            result = service.get("Result")
            exit_code = service.get("ExecMainStatus")
            if result and exit_code is not None:
                r.update(lastResult="success" if result == "success" and exit_code == "0" else "failure",
                         resultDetail=f"Service result: {result}; exit status: {exit_code}")
    except (OSError, subprocess.TimeoutExpired) as error:
        r["note"] = str(error)
    return r

if __name__ == "__main__":
    print(json.dumps(inspect(), separators=(",", ":")))
