"""Require successful, actually executed native upgrade steps on reviewed main.

Used only by explicit publication. A packaging-only or automatic green run is
insufficient. Queries GitHub job evidence; never launches a workflow or package.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

REQUIRED = {
    'Build unpublished newer Windows fixture and verify signed SYSTEM upgrade',
    'Required signed upgrade on Linux Mint 22.3',
}


def completed_native_steps(jobs):
    if not isinstance(jobs, dict) or not isinstance(jobs.get('jobs'), list):
        return False
    # No truncated first-page acceptance.
    if jobs.get('total_count') != len(jobs['jobs']):
        return False
    passed = {step.get('name') for job in jobs['jobs'] if job.get('conclusion') == 'success'
              for step in job.get('steps', []) if step.get('conclusion') == 'success'}
    return REQUIRED <= passed


def require_native_validation(runs, sha, fetch_jobs):
    for run in runs.get('workflow_runs', []):
        if (run.get('head_sha') == sha and run.get('head_branch') == 'main'
                and run.get('event') == 'workflow_dispatch' and run.get('conclusion') == 'success'
                and type(run.get('id')) is int and run['id'] > 0):
            if completed_native_steps(fetch_jobs(run['id'])):
                return
    raise RuntimeError('Successful explicitly dispatched Windows/Mint native upgrade steps on this exact main commit are required')


def main():
    runs = json.loads(Path(sys.argv[1]).read_text())
    repo = os.environ['GITHUB_REPOSITORY']
    def fetch(run_id):
        result = subprocess.run(['gh', 'api', f'repos/{repo}/actions/runs/{run_id}/jobs?per_page=100'],
                                check=True, capture_output=True, text=True)
        return json.loads(result.stdout)
    require_native_validation(runs, os.environ['GITHUB_SHA'], fetch)


if __name__ == '__main__':
    main()
