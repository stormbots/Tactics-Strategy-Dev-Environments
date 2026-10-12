"""Read-only inspection of the fixed system timer and its service."""
import datetime
import json
import os
import re
import stat
import subprocess
from pathlib import Path

TIMER = "skyview-student-dev-update.timer"
SERVICE = "skyview-student-dev-update.service"
LOG_FOLDER = "/var/log/skyview-robotics/student-dev"
HISTORY = Path('/var/lib/skyview-robotics/self-update/maintenance-history.json')

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

def history_time(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('Invalid history timestamp')
    parsed = datetime.datetime.fromisoformat(value)
    if parsed.utcoffset() != datetime.timedelta(0):
        raise ValueError('UTC history required')
    return parsed

def validate_history(record):
    if not isinstance(record, dict) or set(record) != {
            'schemaVersion', 'invocation', 'startedAt', 'completedAt', 'lastResult'}:
        raise ValueError('Invalid maintenance history')
    if type(record['schemaVersion']) is not int or record['schemaVersion'] != 1:
        raise ValueError('Unsupported history schema')
    if not isinstance(record['invocation'], str) or not re.fullmatch('[0-9a-f]{32}', record['invocation']):
        raise ValueError('Invalid invocation')
    start = history_time(record['startedAt'])
    end = record['completedAt']
    if end is not None and history_time(end) < start:
        raise ValueError('Invalid completion time')
    if record['lastResult'] not in ('success', 'failure', 'deferred', 'unavailable'):
        raise ValueError('Invalid history result')
    if end is None and record['lastResult'] != 'unavailable':
        raise ValueError('Incomplete history cannot claim success')
    return record

def read_history():
    try:
        # Never consume a user-writable, linked, oversized or malformed receipt.
        for path in HISTORY.parents:
            m = path.lstat()
            if m.st_uid != 0 or m.st_mode & 0o022 or not stat.S_ISDIR(m.st_mode):
                raise ValueError('Untrusted history ancestor')
        fd = os.open(HISTORY, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            m = os.fstat(stream.fileno())
            if m.st_uid != 0 or m.st_mode & 0o022 or not stat.S_ISREG(m.st_mode) or m.st_nlink != 1:
                raise ValueError('Untrusted history')
            data = stream.read(4097)
        if len(data) > 4096:
            raise ValueError('Oversized history')
        return validate_history(json.loads(data))
    except (OSError, ValueError, TypeError):
        return None

def durable_result(record, service, timer):
    """Use durable history only when no evidence points to a newer invocation."""
    if record is None:
        return None
    invocation = service.get('InvocationID')
    if invocation and invocation != record['invocation']:
        return None
    end = record['completedAt'] or record['startedAt']
    for raw in (service.get('ExecMainStartTimestamp'), timer.get('LastTriggerUSec')):
        current = timestamp(raw)
        if current and history_time(current) > history_time(end):
            return None
    if service.get('Result') not in (None, '', 'success') and record['lastResult'] == 'success':
        return None
    return record

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
        if service.get("ActiveState") in ("active", "activating", "deactivating"):
            r.update(lastResult="running", resultDetail="Maintenance is running.")
        elif (record := durable_result(read_history(), service, timer)) is not None:
            r.update(lastRun=record['startedAt'], lastResult=record['lastResult'],
                     resultDetail=("Recorded maintenance service result: " + record['lastResult'])
                     if record['completedAt'] else "Maintenance was interrupted or has not recorded completion; review protected logs.")
        elif not raw_last or raw_last == "n/a":
            # A persistent timer can retain a trigger from a previous boot while
            # the service's execution result has been discarded by systemd.
            triggered = timestamp(timer.get("LastTriggerUSec"))
            r.update(lastRun=triggered, lastResult="unavailable" if triggered else "never",
                     resultDetail="Service execution history is unavailable; review maintenance logs." if triggered else "No maintenance result is available in the current service history.")
        elif not last:
            r["resultDetail"] = "Last run timestamp is unavailable."
        else:
            result = service.get("Result")
            exit_code = service.get("ExecMainStatus")
            if result and exit_code is not None:
                r.update(lastResult="deferred" if exit_code == "75" else "success" if result == "success" and exit_code == "0" else "failure",
                         resultDetail=f"Service result: {result}; exit status: {exit_code}")
    except (OSError, subprocess.TimeoutExpired) as error:
        r["note"] = str(error)
    return r

if __name__ == "__main__":
    print(json.dumps(inspect(), separators=(",", ":")))
