"""Fixture-only CLI smoke test on disposable Actions Windows/Mint hosts."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import native_uat_fixtures as fixtures


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("SDE_FIXTURE_CI") != "true":
        raise SystemExit("Disposable fixture CI only")
    who = fixtures.identity()  # Actual host identity: never mocked.
    home = Path.home()
    if home != Path(os.environ["SDE_FIXTURE_HOME"]):
        raise SystemExit("Dedicated fixture home required")
    paths = fixtures.targets(who)
    if paths["workspace"].exists() or paths["mentor-repository"].exists() or paths["git-manual"].exists():
        raise SystemExit("Refusing existing workstation data")
    root = home / "fixture state ' $literal"
    paths["workspace"].mkdir()
    paths["mentor-repository"].parent.mkdir(parents=True, exist_ok=True)
    header = b"Name,Url,Folder\r\n" if os.name == "nt" else b"name,url,branch,enabled\n"
    paths["mentor-repository"].write_bytes(header)
    paths["git-manual"].write_bytes(b"[init]\n\tdefaultBranch = main\n# preserve exact bytes\n")
    originals = {key: path.read_bytes() for key, path in paths.items() if key != "workspace"}
    command = [sys.executable, str(Path(__file__).with_name("native_uat_fixtures.py"))]

    def cli(action, *extra, success=True):
        result = subprocess.run([*command, action, "--state-dir", str(root), *extra], text=True, capture_output=True)
        if (result.returncode == 0) != success:
            # Do not print ledger or private configuration contents.
            raise AssertionError(f"{action} unexpected exit {result.returncode}: {result.stderr}")
        return result

    cli("enroll", "--acknowledge-disposable-vm")
    if os.name == "nt":
        script = "$a=Get-Acl -LiteralPath $env:SDE_UAT_STATE_PATH; if(!$a.AreAccessRulesProtected){throw 'Inherited root ACL'}; $s=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; foreach($r in $a.Access){if($r.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -ne $s){throw 'Unexpected principal'}}; if($a.Access.Count -eq 0){throw 'Empty ACL'}"
        import base64
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", base64.b64encode(script.encode("utf-16-le")).decode()], env={**os.environ, "SDE_UAT_STATE_PATH": str(root)}, check=True)
    else:
        assert root.stat().st_mode & 0o777 == 0o700
        assert root.stat().st_uid == os.getuid()
    passed = ["private-state-permissions"]
    for case in ("workspace", "git-manual", "mentor-repository"):
        cli("apply", "--case", case)
        assert json.loads(cli("status").stdout)["active_case"] == case
        if case == "workspace":
            assert not paths[case].exists()
        elif case == "git-manual":
            assert fixtures.run("git", "config", "--global", "--get", "init.defaultBranch") == "uat-fixture"
        else:
            assert "example.invalid" in paths[case].read_text()
        cli("restore")
        cli("restore")
        assert paths["workspace"].is_dir() and not list(paths["workspace"].iterdir())
        for key, original in originals.items():
            assert paths[key].read_bytes() == original
        passed.append(case + "-apply-restore")
    cli("apply", "--case", "git-manual")
    fixture_bytes = paths["git-manual"].read_bytes()
    paths["git-manual"].write_bytes(fixture_bytes + b"# concurrent edit\n")
    cli("restore", success=False)
    assert paths["git-manual"].read_bytes().endswith(b"# concurrent edit\n")
    # Test-owned edit only: return to the known fixture to finish cleanup.
    paths["git-manual"].write_bytes(fixture_bytes)
    cli("restore")
    passed.append("drift-refusal")
    record = {"platform": who["system"], "os": platform.platform(), "python": platform.python_version(),
              "git": fixtures.run("git", "--version"), "helper_sha256": hashlib.sha256(Path(fixtures.__file__).read_bytes()).hexdigest(),
              "checks": passed, "result": "PASS", "scope": "fixture CLI only; no SDE application or desktop UAT"}
    destination = Path(os.environ["SDE_FIXTURE_EVIDENCE"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
