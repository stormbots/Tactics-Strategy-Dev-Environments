"""Fail closed to normal application CI unless a PR changes only fixture support."""
import copy
import json
import os
import re
from pathlib import Path
import subprocess

import yaml

WORKFLOW = ".github/workflows/build-dev-setup.yml"
GATE = "needs.scope.outputs.application_required == 'true'"
APPLICATION_JOBS = ("checks", "native", "update-trust")
# Narrow infrastructure exception: never broaden to arbitrary workflows/tests.
MINT_INFRA_PATHS = {
    '.github/actionlint.yaml',
    '.github/workflows/mint-host-inventory.yml',
    '.github/workflows/mint-host-inventory-checks.yml',
    '.github/workflows/native-uat-fixtures.yml',
    'tests/test_mint_host_inventory.py',
    'tests/mint_media_console.py',
    'tests/mint_media_native.py',
    'tests/test_mint_media_console.py',
    '.github/workflows/mint-media-console-prep.yml',
    'tests/run_mint_media_console.py',
    'tests/test_mint_media_workflow.py',
    'tests/start_mint_preparation_runner.py',
    'tests/test_mint_runner_permissions.py',
    '.github/workflows/mint-checkout-validation.yml',
    'tests/observe_mint_checkout.py',
    'tests/test_mint_checkout_observer.py',
    'tests/mint_session_archive_plan.py',
    'tests/test_mint_session_archive_plan.py',
    'tests/mint_session_archive_native.py',
    'tests/test_mint_session_archive_native.py',
    'tests/mint_archive_supervisor.py',
    'tests/test_mint_archive_supervisor.py',



    'docs/MINT-HOST-INVENTORY.md',
    'tests/ci_scope.py',
    'tests/test_ci_scope.py',
}
FIXTURE_PATHS = {
    ".github/workflows/native-uat-fixtures.yml",
    "tests/native_uat_fixtures.py",
    "tests/test_native_uat_fixtures.py",
    "tests/verify_native_uat_cli.py",
    "tests/run_native_uat_tests.py",
    "tests/ci_scope.py",
    "tests/test_ci_scope.py",
    "docs/UI-MILESTONE-UAT.md",
    "docs/UI-NATIVE-UAT-FIXTURES.md",
    "docs/UI-NATIVE-UAT-EVIDENCE.md",
}


def unchanged_application_workflow(before, after):
    """Permit only scope-job introduction and the three explicit job gates."""
    before = copy.deepcopy(before)
    after = copy.deepcopy(after)
    for workflow in (before, after):
        workflow["jobs"].pop("scope", None)
        for name in APPLICATION_JOBS:
            job = workflow["jobs"][name]
            if job.get("needs") == "scope" and job.get("if") == GATE:
                del job["needs"]
                del job["if"]
    return before == after


def application_required(paths, before=None, after=None):
    if not paths:
        return True
    if any(path not in FIXTURE_PATHS | MINT_INFRA_PATHS | {WORKFLOW} for path in paths):
        return True
    if WORKFLOW in paths:
        if before is None or after is None:
            return True
        try:
            if not unchanged_application_workflow(before, after):
                return True
        except (KeyError, TypeError, AttributeError):
            return True
    return False


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def infrastructure_only_push():
    """Only exact infra-only pushes on main may skip application packaging."""
    if os.environ.get('GITHUB_REF') != 'refs/heads/main':
        return False
    try:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        before, after = event['before'], event['after']
        if (event.get('ref') != 'refs/heads/main'
                or event.get('deleted') is not False
                or after != os.environ.get('GITHUB_SHA')
                or any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{40}', v)
                       or v == '0'*40 for v in (before, after))):
            return False
        paths = git('diff', '--no-renames', '--name-only', '-z', before, after).decode().rstrip('\0').split('\0')
        return bool(paths) and all(p in MINT_INFRA_PATHS for p in paths)
    except (KeyError, OSError, ValueError, TypeError, subprocess.SubprocessError):
        return False


def main():
    required = True
    if os.environ.get("CI_EVENT_NAME") == "pull_request":
        base = os.environ["CI_BASE_SHA"]
        head = os.environ["CI_HEAD_SHA"]
        base = git("merge-base", base, head).decode().strip()
        # No path count truncation; disabling rename detection checks both names.
        paths = git("diff", "--no-renames", "--name-only", "-z", base, head).decode().rstrip("\0").split("\0")
        before = after = None
        if WORKFLOW in paths:
            before = yaml.load(git("show", f"{base}:{WORKFLOW}"), Loader=yaml.BaseLoader)
            after = yaml.load(git("show", f"{head}:{WORKFLOW}"), Loader=yaml.BaseLoader)
        required = application_required(paths, before, after)
    elif os.environ.get('CI_EVENT_NAME') == 'push':
        required = not infrastructure_only_push()
    value = str(required).lower()
    print(f"Application CI required: {value}")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"application_required={value}\n")


if __name__ == "__main__":
    main()
