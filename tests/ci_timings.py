"""Read-only job timing summary; runner seconds are not GitHub billing minutes."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess


def seconds(start, end):
    return (datetime.fromisoformat(end.replace('Z', '+00:00')) -
            datetime.fromisoformat(start.replace('Z', '+00:00'))).total_seconds()


def summarize(jobs):
    completed = [j for j in jobs if j.get('conclusion') not in (None, 'skipped')
                 and j.get('started_at') and j.get('completed_at')]
    return {
        'all_jobs_successful': bool(completed) and all(
            j.get('conclusion') in ('success', 'skipped') for j in jobs),
        'observed_job_span_seconds': seconds(
            min(j['started_at'] for j in completed),
            max(j['completed_at'] for j in completed)) if completed else None,
        'completed_runner_seconds': sum(seconds(j['started_at'], j['completed_at'])
                                        for j in completed),
        'jobs': [{
            'name': j['name'], 'conclusion': j.get('conclusion'),
            'seconds': seconds(j['started_at'], j['completed_at'])
            if j.get('started_at') and j.get('completed_at') else None,
            'steps': [{'name': s['name'],
                       'seconds': seconds(s['started_at'], s['completed_at'])}
                      for s in j.get('steps', []) if s.get('conclusion') == 'success'
                      and s.get('started_at') and s.get('completed_at')],
        } for j in jobs],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--run', type=int)
    source.add_argument('--input', type=Path, help='Saved GitHub jobs API JSON')
    args = parser.parse_args()
    if args.input:
        pages = json.loads(args.input.read_text())
    else:
        lines = subprocess.check_output([
            'gh', 'api', '--paginate', '--jq', '.jobs[] | @json',
            f'repos/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/{args.run}/jobs',
        ], text=True)
        pages = [{'jobs': [json.loads(line) for line in lines.splitlines() if line.strip()]}]
    if isinstance(pages, dict):
        pages = [pages]
    print(json.dumps(summarize([job for page in pages for job in page['jobs']]), indent=2))


if __name__ == '__main__':
    main()
