"""Set only application identities in a disposable candidate build checkout."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ("1.2.2", "1.2.3", "1.2.4", "1.2.5", "1.2.6", "1.2.7", "1.2.8", "1.2.9", "1.2.10", "1.2.11")


def prepare(root, version):
    if version not in VERSIONS:
        raise ValueError("Only the fixed UAT candidates are supported")
    for relative in ("installer/package.json", "installer/package-lock.json",
                     "installer/src-tauri/tauri.conf.json"):
        path = root / relative
        data = json.loads(path.read_text())
        data["version"] = version
        if relative.endswith("package-lock.json"):
            data["packages"][""]["version"] = version
        path.write_text(json.dumps(data, indent=2) + "\n")
    cargo = root / "installer/src-tauri/Cargo.toml"
    text, count = re.subn(r'(?m)^(version = ")[^"]+("\s*)$',
                         lambda m: m[1] + version + m[2], cargo.read_text(), count=1)
    if count != 1:
        raise ValueError("Application Cargo identity missing")
    cargo.write_text(text)
    lock = root / "installer/src-tauri/Cargo.lock"
    text, count = re.subn(r'(\[\[package\]\]\nname = "skyview-dev-setup"\nversion = ")[^"]+("\n)',
                         lambda m: m[1] + version + m[2], lock.read_text())
    if count != 1:
        raise ValueError("Application lock identity missing")
    lock.write_text(text)


if __name__ == "__main__":
    prepare(ROOT, sys.argv[1])
