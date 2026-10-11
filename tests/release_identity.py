"""Fail publication when the canonical release tag disagrees with build inputs."""
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def validate(tag):
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError("Expected a canonical stable release tag")
    versions = [
        json.loads((ROOT / "installer/package.json").read_text())["version"],
        json.loads((ROOT / "installer/src-tauri/tauri.conf.json").read_text())["version"],
        tomllib.loads((ROOT / "installer/src-tauri/Cargo.toml").read_text())["package"]["version"],
    ]
    if any(version != tag[1:] for version in versions):
        raise ValueError("Release tag does not match all application build versions")

if __name__ == "__main__":
    validate(sys.argv[1])
