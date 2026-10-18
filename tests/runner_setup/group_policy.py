"""Pure checks of administrator-exported runner-group snapshots; no API mutation."""
import argparse
import json
import re
from pathlib import Path

REPO = 'stormbots/Tactics-Strategy-Dev-Environments'
WORKFLOW = REPO + '/.github/workflows/mint-host-inventory.yml@refs/heads/main'


def validate(group, repositories, approved_sha):
    failures = []
    for key, expected in {'name': 'sde-mint-isolated', 'visibility': 'selected',
                          'allows_public_repositories': True,
                          'restricted_to_workflows': True, 'default': False}.items():
        if type(group.get(key)) is not type(expected) or group[key] != expected:
            failures.append(key)
    if group.get('selected_workflows') != [WORKFLOW]:
        failures.append('selected_workflows')
    repos = repositories.get('repositories', [])
    if (repositories.get('total_count') != 1 or len(repos) != 1
            or repos[0].get('full_name') != REPO
            or repos[0].get('private') is not False):
        failures.append('selected_repositories')
    if not re.fullmatch('[0-9a-f]{40}', approved_sha):
        failures.append('approved_sha')
    return failures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('group', type=Path)
    p.add_argument('repositories', type=Path)
    p.add_argument('approved_sha')
    a = p.parse_args()
    failures = validate(json.loads(a.group.read_text()),
                        json.loads(a.repositories.read_text()), a.approved_sha)
    print(json.dumps({'snapshotPolicyPass': not failures, 'failures': failures,
                      'livePolicyVerified': False, 'registrationAuthorized': False}))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
