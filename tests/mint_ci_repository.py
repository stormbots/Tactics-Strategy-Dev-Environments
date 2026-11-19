"""Select Mint's official HTTPS mirror in disposable CI userlands only."""
import os
from pathlib import Path
import re

SOURCE = Path("/etc/apt/sources.list.d/official-package-repositories.list")
NEW = b"https://fastly.linuxmint.io"


def repository_bytes(data):
    """Preserve every byte except the single expected Mint repository URI."""
    if len(data) > 65536:
        raise ValueError("Unexpected Mint source file size")
    lines = data.splitlines(keepends=True)
    found = []
    for index, line in enumerate(lines):
        if line.lstrip().startswith(b"#"):
            continue
        if b"packages.linuxmint.com" not in line and NEW not in line:
            continue
        # Refuse options, other suites/components, or an already-customized URI.
        match = re.fullmatch(
            rb"([ \t]*deb[ \t]+)(http://packages\.linuxmint\.com/?|https://fastly\.linuxmint\.io/?)"
            rb"([ \t]+zena[ \t]+main[ \t]+upstream[ \t]+import[ \t]+backport[ \t]*(?:#id:linuxmint_main[ \t]*)?(?:\r?\n)?)",
            line,
        )
        if match is None:
            raise ValueError("Unexpected Mint repository definition")
        found.append(index)
        uri = match[2]
        replacement = NEW + (b"/" if uri.endswith(b"/") else b"")
        lines[index] = match[1] + replacement + match[3]
    if len(found) != 1:
        raise ValueError("Expected exactly one default Mint repository")
    return b"".join(lines)


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.geteuid() != 0:
        raise SystemExit("Disposable root CI container required")
    release = Path("/etc/os-release").read_text()
    if not re.search(r'^ID=["\']?linuxmint["\']?$', release, re.M) or not re.search(
        r'^VERSION_ID=["\']?22\.3["\']?$', release, re.M
    ):
        raise SystemExit("Actual Mint 22.3 CI userland required")
    # Fixed path, no caller-selected endpoint, trust options, keyring, or suite.
    with SOURCE.open("r+b") as source:
        original = source.read(65537)
        updated = repository_bytes(original)
        if updated != original:
            source.seek(0)
            source.write(updated)
            source.truncate()
    print("Mint CI repository: official HTTPS mirror; APT signature checks required")


if __name__ == "__main__":
    main()
