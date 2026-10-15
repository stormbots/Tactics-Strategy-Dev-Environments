"""Opt-in, reversible native UAT conditions. Never provisions or runs SDE."""
import argparse
import base64
import csv
import getpass
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def identity():
    if os.name == "nt":
        system = "windows"
    else:
        values = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
        if values.get("ID", "").strip('"') != "linuxmint":
            raise ValueError("Native fixtures require Windows or Linux Mint")
        if os.getuid() == 0:
            raise ValueError("Run as the dedicated desktop test account, not root")
        system = "mint"
    return {"system": system, "host": platform.node(), "user": getpass.getuser(), "home": str(Path.home().resolve())}


def regular(path, directory=False):
    # Reject links/junctions anywhere in a target path, including absent leaves.
    for item in (path, *path.parents):
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise ValueError("Linked fixture paths are not supported")
    if directory:
        if not path.is_dir():
            raise ValueError("Expected an existing directory")
    elif path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
        raise ValueError("Expected a regular, unshared file")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(root, state):
    # Durable intent is saved before any target mutation.
    temporary = root / "state.tmp"
    regular(temporary)
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(root / "state.json")


def secure(root):
    regular(root, directory=True)
    if os.name == "nt":
        # Backups may contain private Git configuration. Disable inherited ACLs.
        script = "$p=$env:SDE_UAT_STATE_PATH; $s=[Security.Principal.WindowsIdentity]::GetCurrent().User; $a=New-Object Security.AccessControl.DirectorySecurity; $a.SetOwner($s); $a.SetAccessRuleProtection($true,$false); $r=New-Object Security.AccessControl.FileSystemAccessRule($s,'FullControl','ContainerInherit,ObjectInherit','None','Allow'); $a.AddAccessRule($r); Set-Acl -LiteralPath $p -AclObject $a -ErrorAction Stop"
        encoded = base64.b64encode(script.encode("utf-16-le")).decode()
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                       env={**os.environ, "SDE_UAT_STATE_PATH": str(root)},
                       check=True, capture_output=True, text=True)
    else:
        if root.stat().st_uid != os.getuid():
            raise ValueError("Fixture directory must belong to this account")
        root.chmod(0o700)


def enroll(root, acknowledge):
    if not acknowledge:
        raise ValueError("Explicit disposable-VM acknowledgement required")
    who = identity()
    workspace = targets(who)["workspace"].absolute()
    if root == workspace or workspace in root.parents:
        raise ValueError("Fixture state must be outside Development")
    if root.exists():
        raise ValueError("Use a new fixture-state directory")
    regular(root)
    root.mkdir(mode=0o700)
    secure(root)
    save(root, {"schema": 1, "identity": who, "active": None})


def load(root):
    regular(root, directory=True)
    regular(root / "state.json")
    state = json.loads((root / "state.json").read_text())
    if state.get("schema") != 1 or state.get("identity") != identity():
        raise ValueError("Fixture state belongs to another host/account/profile")
    secure(root)
    return state


def targets(who):
    home = Path(who["home"])
    return {
        "workspace": Path("C:/Development") if who["system"] == "windows" else home / "Development",
        "git-manual": home / ".gitconfig",
        "mentor-repository": Path("C:/ProgramData/SkyviewRobotics/repositories.csv") if who["system"] == "windows" else Path("/etc/skyview-robotics/student-dev/repositories.csv"),
    }


def apply(root, case):
    state = load(root)
    if state["active"]:
        raise ValueError("Restore the active case first")
    path = targets(state["identity"])[case]
    regular(path, directory=case == "workspace")
    if case == "workspace":
        if any(path.iterdir()):
            raise ValueError("Workspace must be empty; existing work is never moved")
        parked = path.with_name("Development.sde-uat-parked")
        regular(parked)
        if parked.exists():
            raise ValueError("Parked workspace already exists")
        active = {"case": case, "path": str(path), "parked": str(parked)}
    else:
        if not path.is_file() or not os.access(path, os.W_OK):
            raise ValueError("Existing writable fixture configuration required")
        original = path.read_bytes()
        if case == "git-manual":
            if any(key.startswith("GIT_CONFIG") for key in os.environ):
                raise ValueError("Git configuration environment overrides are unsupported")
            xdg = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "git/config"
            if xdg.exists():
                raise ValueError("Additional XDG Git configuration is unsupported")
            if run("git", "config", "--global", "--get", "init.defaultBranch") != "main":
                raise ValueError("Start from the verified main-branch baseline")
            with tempfile.TemporaryDirectory(dir=root) as directory:
                candidate = Path(directory) / "gitconfig"
                candidate.write_bytes(original)
                run("git", "config", "--file", str(candidate), "--replace-all", "init.defaultBranch", "uat-fixture")
                fixture = candidate.read_bytes()
        else:
            text = original.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            expected = ["Name", "Url", "Folder"] if state["identity"]["system"] == "windows" else ["name", "url", "branch", "enabled"]
            if reader.fieldnames != expected or list(reader):
                raise ValueError("Repository configuration must contain only the stock header")
            missing = targets(state["identity"])["workspace"] / "sde-uat-missing-project"
            if missing.exists():
                raise ValueError("Fixture project already exists")
            row = "sde-uat-missing-project,https://example.invalid/uat-only.git,"
            fixture = (",".join(expected) + "\n" + row + ("sde-uat-missing-project\n" if expected[0] == "Name" else "main,true\n")).encode()
        active = {"case": case, "path": str(path), "original": base64.b64encode(original).decode(), "fixture": digest(fixture)}
    state["active"] = active
    save(root, state)
    if case == "workspace":
        path.rename(parked)
    else:
        path.write_bytes(fixture)  # Preserve the existing file's ownership and ACL.
        if case == "git-manual" and run("git", "config", "--global", "--get", "init.defaultBranch") != "uat-fixture":
            raise ValueError("Included Git settings override the fixture; restore before proceeding")
    print("Fixture active. Run native Validate; do not run Install/Repair/Update in mentor-repository.")


def restore(root):
    state = load(root)
    active = state["active"]
    if not active:
        return
    case = active["case"]
    path = targets(state["identity"])[case]
    if str(path) != active["path"]:
        raise ValueError("Unexpected fixture target")
    if case == "workspace":
        regular(path, directory=path.exists())
        parked = path.with_name("Development.sde-uat-parked")
        if str(parked) != active["parked"]:
            raise ValueError("Unexpected parked workspace")
        regular(parked, directory=parked.exists())
        if path.exists() and parked.exists():
            raise ValueError("Workspace recreated; preserve it and revert the VM snapshot")
        source = parked if parked.exists() else path
        regular(source, directory=True)
        if any(source.iterdir()):
            raise ValueError("Workspace contains new work; revert the VM snapshot")
        if parked.exists():
            parked.rename(path)
    else:
        regular(path)
        original = base64.b64decode(active["original"], validate=True)
        if not path.is_file() or digest(path.read_bytes()) not in (digest(original), active["fixture"]):
            raise ValueError("Configuration changed; refusing to overwrite it. Revert snapshot")
        path.write_bytes(original)
        if path.read_bytes() != original:
            raise ValueError("Restoration verification failed")
    state["active"] = None
    save(root, state)
    print("Original state restored and verified. Rerun native Validate.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["enroll", "apply", "restore", "status"])
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--case", choices=["workspace", "git-manual", "mentor-repository"])
    parser.add_argument("--acknowledge-disposable-vm", action="store_true")
    args = parser.parse_args()
    root = args.state_dir.absolute()
    if args.action == "enroll":
        enroll(root, args.acknowledge_disposable_vm)
    else:
        execute(args, root)


def execute(args, root):
    load(root)
    lock = root / "operation.lock"
    regular(lock)
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        dispatch(args, root)
    finally:
        os.close(descriptor)
        lock.unlink()


def dispatch(args, root):
    if args.action == "apply":
        if not args.case:
            raise ValueError("apply requires --case")
        apply(root, args.case)
    elif args.action == "restore":
        restore(root)
    else:
        state = load(root)
        print(json.dumps({"identity": state["identity"], "active_case": (state["active"] or {}).get("case")}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Fixture stopped: {error}") from error
