"""Read-only inspection of the fixed system timer and its service."""
import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

TIMER = "skyview-student-dev-update.timer"
SERVICE = "skyview-student-dev-update.service"
LOG_FOLDER = "/var/log/skyview-robotics/student-dev"
HISTORY = Path('/var/lib/skyview-robotics/self-update/maintenance-history.json')

class InspectionError(OSError):
    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def show(unit):
    try:
        p = subprocess.run(["/usr/bin/systemctl", "show", unit, "--no-pager"],
                           capture_output=True, text=True, timeout=10, check=False,
                           env={**os.environ, "LC_ALL": "C", "TZ": "UTC"})
    except PermissionError as error:
        raise InspectionError("accessDenied", "SDE does not have permission to read maintenance information.") from error
    except subprocess.TimeoutExpired as error:
        raise InspectionError("timedOut", "The maintenance check took too long and did not finish.") from error
    except OSError as error:
        raise InspectionError("readFailed", "The system could not provide maintenance information.") from error
    if p.returncode:
        # Match only the service manager's named D-Bus error, never unit data.
        denied = "org.freedesktop.DBus.Error.AccessDenied" in p.stderr
        raise InspectionError("accessDenied" if denied else "readFailed",
                              "SDE does not have permission to read maintenance information." if denied else
                              "The system could not provide maintenance information.")
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

def context_file(path, limit):
    """Bounded normal-user read; context is display data, never execution authority."""
    for parent in path.parents:
        metadata = parent.lstat()
        if metadata.st_uid != 0 or metadata.st_mode & 0o022 or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError('Unverified context ancestor')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if before.st_uid != 0 or before.st_mode & 0o022 or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('Unverified context file')
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        identity = lambda m: (m.st_dev, m.st_ino, m.st_size, m.st_mtime_ns, m.st_ctime_ns)
        if len(data) > limit or identity(before) != identity(after):
            raise ValueError('Incomplete context read')
    return data


def choice_context(timer, service):
    """Recognize only the fixed installed unit layout; unsupported layouts omit context."""
    try:
        machine = context_file(Path('/etc/machine-id'), 33).strip()
        if not re.fullmatch(b'[0-9a-f]{32}', machine) or machine == b'0' * 32:
            return None
        definitions = []
        for unit, record in ((TIMER, timer), (SERVICE, service)):
            expected = '/etc/systemd/system/' + unit
            if record.get('FragmentPath') != expected or record.get('NeedDaemonReload') != 'no':
                return None
            paths = [expected]
            dropins = record.get('DropInPaths', '')
            if dropins:
                # Current installed history hooks. Other layouts require review.
                known = '/etc/systemd/system/' + SERVICE + '.d/sde-self-update.conf'
                if unit != SERVICE or dropins != known:
                    return None
                paths.append(known)
            for path in paths:
                definitions.append([path, context_file(Path(path), 65536).decode('utf-8')])
        if not definitions[0][1].strip() or not definitions[1][1].strip():
            return None
        payload = json.dumps(definitions, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        return dict(machineId=hashlib.sha256(b'sde-maintenance-machine-v1\0' + machine).hexdigest(),
                    identifier=TIMER, definitionId=hashlib.sha256(payload).hexdigest())
    except (OSError, ValueError, UnicodeError):
        return None


def inspect():
    observed = datetime.datetime.now(datetime.timezone.utc).isoformat()
    r = dict(status="unavailable", active=False, identifier=TIMER, frequency="Unavailable",
             nextRun=None, lastRun=None, lastResult="unavailable", resultDetail="Unavailable",
             catchUp=None, logFolder=LOG_FOLDER, logsAvailable=Path(LOG_FOLDER).is_dir(), note="",
             observedAt=observed, createdAt=None, lastSuccess=None,
             inspectionScope="schedule", inspectionReason="unknown")
    try:
        timer = show(TIMER)
        if timer.get("LoadState") == "not-found":
            return {**r, "status": "missing", "inspectionReason": "notInstalled", "note": "Weekly maintenance is not installed. Review the schedule before choosing any setup changes."}
        if timer.get("LoadState") != "loaded":
            raise InspectionError("readFailed", "The maintenance timer could not be loaded.")
        state = timer.get("UnitFileState")
        if state not in ("enabled", "enabled-runtime", "disabled"):
            raise InspectionError("unknown", "The system returned a timer state SDE could not verify.")
        enabled = state in ("enabled", "enabled-runtime")
        active = timer.get("ActiveState") == "active"
        calendars = re.findall(r"OnCalendar=(.*?) ;", timer.get("TimersCalendar", ""))
        frequency = "; ".join(calendars) or "No calendar trigger"
        delay = timer.get("RandomizedDelayUSec", "0")
        if delay not in ("0", "0us", ""):
            frequency += f"; randomized delay up to {delay}"
        r.update(status="enabled" if enabled else "disabled", active=active, inspectionReason="verified",
                 frequency=frequency + " (system local time unless the calendar specifies a zone)",
                 nextRun=timestamp(timer.get("NextElapseUSecRealtime")) if active else None,
                 catchUp={"yes": True, "no": False}.get(timer.get("Persistent")),
                 note=("Automatic development-tool maintenance will not run on future boots while the timer is disabled."
                       if not enabled else "" if active else "The timer is enabled but is not waiting for its next run. Review the schedule."))
        # Inspect only the owned service. Do not accept a service name from UI.
        r["inspectionScope"] = "history"
        service = show(SERVICE)
        if service.get("LoadState") != "loaded":
            r["inspectionReason"] = "notInstalled" if service.get("LoadState") == "not-found" else "readFailed"
            r["note"] = "SDE could not read the maintenance service information. Review the schedule and save a support report if the check still fails."
            return r
        r["inspectionScope"] = "schedule"
        context = choice_context(timer, service)
        if context is not None:
            r["choiceContext"] = context
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
        if r["lastResult"] == "success":
            r["lastSuccess"] = r["lastRun"]
    except (OSError, subprocess.TimeoutExpired) as error:
        r["inspectionReason"] = (error.reason if isinstance(error, InspectionError) else
                                 "accessDenied" if isinstance(error, PermissionError) else
                                 "timedOut" if isinstance(error, subprocess.TimeoutExpired) else "readFailed")
        if isinstance(error, subprocess.TimeoutExpired):
            r["note"] = "The maintenance check took too long and did not finish."
        elif isinstance(error, PermissionError):
            r["note"] = "SDE does not have permission to read maintenance information."
        else:
            # Retain a bounded diagnostic for existing report consumers. The UI
            # uses the structured cause, never this text, to explain the finding.
            r["note"] = str(error)[:1024]

    return r

def validation_message(record):
    """Scheduling is information, never proof of tool health or native activity."""
    status = record['status']
    if status == 'disabled':
        # A disabled unit can remain active until shutdown. Do not claim it
        # cannot fire in this session or silently stop it.
        return ('Weekly maintenance is disabled. The timer may still run in this session.'
                if record['active'] else
                'Weekly maintenance is disabled. Future automatic development-tool maintenance is not scheduled.') + ' Review Schedule.'
    if status == 'missing':
        return 'Weekly maintenance timer is missing. Review Schedule before choosing any setup changes.'
    if status == 'enabled':
        if not record['active']:
            return 'Weekly maintenance timer is enabled but inactive. Review Schedule.'
        return 'Weekly maintenance timer is enabled. View Schedule for its next run and earlier results.'
    return 'Weekly maintenance could not be checked. Review Schedule and save a support report if the check still fails.'


def main(args):
    if args not in ([], ['--validation']):
        raise SystemExit('Unsupported schedule inspection option')
    record = inspect()
    if args:
        print('SKYVIEW_EVENT|validation|INFO|' + validation_message(record))
    else:
        print(json.dumps(record, separators=(',', ':')))


if __name__ == "__main__":
    main(sys.argv[1:])
