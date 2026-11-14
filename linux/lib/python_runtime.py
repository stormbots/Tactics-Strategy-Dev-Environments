"""Verify one required Python and its disposable project environment; no provisioning."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass

IDENTITY = ('import json,sys; print(json.dumps({"version":"%d.%d.%d" % sys.version_info[:3],'
            '"executable":sys.executable,"baseExecutable":getattr(sys,"_base_executable",sys.executable),"prefix":sys.prefix,"basePrefix":sys.base_prefix}))')

@dataclass(frozen=True)
class Probe:
    code: int
    text: str = ""
    reason: str = "completed"


def diagnostic(arguments, timeout):
    if timeout <= 0:
        return Probe(-1, reason="timeout")
    try:
        # This separate process group contains only our fixed diagnostic/venv
        # children, never an installer or another user's existing process.
        with subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              start_new_session=True) as process:
            try:
                stdout, _ = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    process.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    # Do not wait indefinitely if an unexpected descendant kept
                    # a pipe open. We never target a process outside our group.
                    process.stdout.close()
                    process.stderr.close()
                return Probe(-1, reason="timeout")
            if len(stdout) > 16384:
                return Probe(-1, reason="invalidOutput")
            return Probe(process.returncode, stdout.decode("utf-8", errors="strict").strip())
    except (OSError, UnicodeError):
        return Probe(-1, reason="unavailable")


def executable(value):
    return (isinstance(value, str) and 0 < len(value) <= 4096 and value.startswith("/")
            and not re.search(r"[\x00-\x1f|]", value)
            and Path(value).is_file() and os.access(value, os.X_OK))


def identity(probe):
    if probe.code != 0:
        return None
    try:
        value = json.loads(probe.text)
        if (not isinstance(value, dict) or set(value) != {"version", "executable", "baseExecutable", "prefix", "basePrefix"}
                or not isinstance(value["version"], str)
                or not re.fullmatch(r"3\.14\.\d{1,8}", value["version"])
                or not isinstance(value["prefix"], str) or not os.path.isabs(value["prefix"])
                or not isinstance(value["basePrefix"], str) or not os.path.isabs(value["basePrefix"])
                or not executable(value["executable"]) or not executable(value["baseExecutable"])):
            return None
        return value
    except (ValueError, TypeError, OSError):
        return None


def verify(run=diagnostic, find=shutil.which):
    record = dict(schema=1, component="Python", requiredFamily="3.14", status="incomplete",
                  reason="discoveryIncomplete", version=None, executable=None, pipVersion=None)
    deadline = time.monotonic() + 30

    def query(arguments, limit):
        remaining = max(0, min(limit, deadline - time.monotonic()))
        return run(arguments, remaining) if remaining else Probe(-1, reason="timeout")

    def failed(probe, reason):
        record["status"] = "incomplete" if probe.reason in ("timeout", "invalidOutput", "unavailable") else "unusable"
        record["reason"] = reason + "Timeout" if probe.reason == "timeout" else reason + "Failed"
        return record

    try:
        # System/default Python is untouched. Only the explicit family command
        # is discovered; sys.executable then binds every related probe.
        candidate = find("python3.14")
        if not candidate:
            record.update(status="notFound", reason="notDiscovered")
            return record
        if not executable(candidate):
            return record
        probe = query([candidate, "-I", "-B", "-c", IDENTITY], 3)
        selected = identity(probe)
        if not selected:
            return failed(probe, "interpreter")
        selected_path = selected["executable"]
        probe = query([selected_path, "-I", "-B", "-c", IDENTITY], 3)
        confirmed = identity(probe)
        if not confirmed or not os.path.samefile(selected_path, confirmed["executable"]):
            return failed(probe, "interpreter")
        record.update(version=confirmed["version"], executable=selected_path)
        # Linux requires project-local pip, not installation into system Python.
        with tempfile.TemporaryDirectory(prefix="sde-python-check-") as directory:
            environment = Path(directory) / "venv"
            probe = query([selected_path, "-I", "-B", "-m", "venv", str(environment)], 20)
            if probe.code != 0:
                return failed(probe, "venv")
            project_python = str(environment / "bin" / "python")
            if not executable(project_python):
                record.update(status="unusable", reason="venvFailed")
                return record
            probe = query([project_python, "-I", "-B", "-c", IDENTITY], 3)
            project = identity(probe)
            if (not project or not os.path.samefile(selected_path, project["baseExecutable"])
                    or Path(project["prefix"]).resolve() != environment.resolve()
                    or Path(project["basePrefix"]).resolve() == environment.resolve()):
                return failed(probe, "venv")
            probe = query([project_python, "-I", "-B", "-m", "pip", "--version"], 4)
            match = re.fullmatch(r"pip ([0-9][A-Za-z0-9.!+_-]{0,119}) .+ \(python 3\.14\)", probe.text)
            if probe.code != 0 or not match:
                return failed(probe, "pip")
            record.update(status="passed", reason="verified", pipVersion=match[1])
            return record
    except (OSError, ValueError, TypeError):
        # Permission/missing-file/cleanup/discovery errors are not absence.
        record.update(status="incomplete", reason="discoveryIncomplete", pipVersion=None)
        return record


def report(record):
    print("SKYVIEW_EVENT|runtime|Python|" + json.dumps(record, separators=(",", ":")))
    status = "PASS" if record["status"] == "passed" else "FAIL"
    if status == "PASS":
        message = f'Python: {record["version"]}; test project environment and its pip {record["pipVersion"]} verified'
    elif record["status"] == "notFound":
        message = "Python: the supported search did not find Python 3.14. Other versions can stay installed."
    elif record["status"] == "incomplete":
        message = "Python: SDE could not finish checking Python 3.14. This does not mean it is missing."
    else:
        message = "Python: Python 3.14 or its test project environment did not work. Review the check details."
    print(f"SKYVIEW_EVENT|validation|{status}|{message}")
    print(f"{status}  {message}")
    return 0 if status == "PASS" else 10


if __name__ == "__main__":
    raise SystemExit(report(verify()))
