"""Classify bounded PR validation; unknown changes retain full native CI."""
import json
import os
import re
from pathlib import Path
import subprocess


WORKFLOW = ".github/workflows/build-dev-setup.yml"
GATE = "needs.scope.outputs.application_required == 'true' || needs.scope.outputs.documentation_required == 'true'"
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
}
POLICY_PATHS = {"tests/ci_scope.py", "tests/test_ci_scope.py", "tests/check_docs.py", "tests/test_check_docs.py"}
MINT_INFRA_PATHS |= {"tests/ci_scope.py", "tests/test_ci_scope.py"}
FIXTURE_PATHS = {
    ".github/workflows/native-uat-fixtures.yml",
    "tests/native_uat_fixtures.py",
    "tests/test_native_uat_fixtures.py",
    "tests/verify_native_uat_cli.py",
    "tests/run_native_uat_tests.py",
    "docs/UI-MILESTONE-UAT.md",
    "docs/UI-NATIVE-UAT-FIXTURES.md",
    "docs/UI-NATIVE-UAT-EVIDENCE.md",
}


# Register any Markdown used as executable configuration when adding its consumer.
# Release-note prose is a reference, not an execution/configuration input.
FULL_REFERENCE_PATHS = frozenset()


def documentation_path(path):
    """Only inert reference formats in approved locations; never a blanket docs/ exemption."""
    from pathlib import PurePosixPath
    parsed = PurePosixPath(path)
    if str(parsed) != path or ".." in parsed.parts or parsed.is_absolute():
        return False
    if path in FULL_REFERENCE_PATHS:
        return False
    if path == "README.md":
        return True
    return (path.startswith("docs/") and parsed.name != "AGENTS.md"
            and parsed.suffix.lower() in {".md", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"})


def application_required(paths, before=None, after=None):
    # Workflow and policy changes always validate the full pipeline themselves.
    if not paths or set(paths) & (POLICY_PATHS | {WORKFLOW}):
        return True
    return any(not documentation_path(path) and path not in FIXTURE_PATHS | MINT_INFRA_PATHS
               for path in paths)


# Deliberately explicit: new files need a reviewed classification. Native bridge,
# recovery/consent APIs, dependencies, packaging and workflows are not included.
PRESENTATION_PATHS = {
    "installer/src/style.css", "installer/src/AppearanceControls.tsx",
    "installer/src/ThemeControl.tsx", "installer/src/ZoomControl.tsx",
    "docs/overview-next-step-demo/index.html", "docs/overview-next-step-demo/verify.cjs",
}
PRESENTATION_PATHS |= {
    p.removesuffix(".tsx") + ".test.tsx" if p.endswith(".tsx")
    else p.removesuffix(".ts") + ".test.ts"
    for p in tuple(PRESENTATION_PATHS) if p.endswith((".ts", ".tsx"))
}


def native_required(paths, event):
    # Presentation shortcuts are PR-only. Documentation may accompany them.
    return not (event == "pull_request" and bool(paths)
                and all(path in PRESENTATION_PATHS or documentation_path(path) for path in paths))


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def main_push_paths():
    """Read the exact pushed range; malformed metadata cannot earn a shortcut."""
    if os.environ.get('GITHUB_REF') != 'refs/heads/main':
        return None
    try:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        before, after = event['before'], event['after']
        if (event.get('ref') != 'refs/heads/main'
                or event.get('deleted') is not False
                or after != os.environ.get('GITHUB_SHA')
                or any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{40}', v)
                       or v == '0'*40 for v in (before, after))):
            return None
        return git('diff', '--no-renames', '--name-only', '-z', before, after).decode().rstrip('\0').split('\0')
    except (KeyError, OSError, ValueError, TypeError, subprocess.SubprocessError):
        return None


def infrastructure_only_push():
    paths = main_push_paths()
    return (bool(paths) and not (set(paths) & POLICY_PATHS)
            and all(p in MINT_INFRA_PATHS for p in paths))


def classify(paths, event, ref='', unsafe_documents=()):
    """Return (application, native, documentation), with full as the default."""
    if not paths or not all(paths):
        return True, True, False
    documents = any(documentation_path(path) for path in paths)
    if event not in ('pull_request', 'push') or (event == 'push' and ref != 'refs/heads/main'):
        return True, True, documents
    if unsafe_documents or set(paths) & (POLICY_PATHS | {WORKFLOW}):
        return True, True, documents
    application = application_required(paths)
    if event == 'push':
        # Preserve the existing infrastructure-only main exception. Other
        # fixture pushes remain full; reference-only main merges stay cheap.
        application = not all(documentation_path(p) or p in MINT_INFRA_PATHS for p in paths)
    return application, application and native_required(paths, event), documents


def unsafe_documentation_paths(paths, base, head):
    # A symlink or executable with a documentation suffix is not inert prose.
    unsafe = set()
    for revision in (base, head):
        tree = git('ls-tree', '-r', '-z', revision, '--', 'README.md', 'docs').decode()
        for row in tree.split('\0'):
            if not row:
                continue
            metadata, path = row.split('\t', 1)
            if path in paths and documentation_path(path) and metadata.split()[0] != '100644':
                unsafe.add(path)
    return unsafe


def main():
    event = os.environ.get('CI_EVENT_NAME')
    ref = os.environ.get('GITHUB_REF', '')
    paths = None
    base = head = None
    if event == 'pull_request':
        head = os.environ['CI_HEAD_SHA']
        base = git('merge-base', os.environ['CI_BASE_SHA'], head).decode().strip()
        paths = git('diff', '--no-renames', '--name-only', '-z', base, head).decode().rstrip('\0').split('\0')
    elif event == 'push':
        paths = main_push_paths()
        if paths:
            payload = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
            base, head = payload['before'], payload['after']
    unsafe = unsafe_documentation_paths(paths, base, head) if paths and any(map(documentation_path, paths)) else ()
    application, native, documents = classify(paths, event, ref, unsafe)
    values = dict(application_required=application, native_required=native, documentation_required=documents)
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        for name, value in values.items():
            output.write(f'{name}={str(value).lower()}\n')
        output.write('documentation_paths=' + json.dumps([p for p in (paths or []) if documentation_path(p)], ensure_ascii=True) + '\n')
    print('Validation scope: ' + json.dumps(values, sort_keys=True))


if __name__ == '__main__':
    main()
