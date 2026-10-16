"""Run W1 locally; stdout is a JSON evidence report. No workflows or native operations."""
import ast
import hashlib
import json
import platform
from pathlib import Path
import sys
import unittest

from model import explore
from durability import timeline
from timing import Budget
from framing import Controller, Rejected

ROOT = Path(__file__).resolve().parent
ALLOWED_IMPORTS = {
    'ast', 'collections', 'dataclasses', 'hashlib', 'hmac', 'json', 'pathlib',
    'platform', 'random', 're', 'struct', 'math', 'sys', 'tempfile', 'unittest',
    'model', 'framing', 'durability', 'timing',
}


def scope_review():
    """Static deny-by-allowlist aid, not an OS sandbox/security proof."""
    imports = set()
    for path in ROOT.glob('*.py'):
        tree = ast.parse(path.read_text(), str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or '').split('.')[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {'eval', 'exec', '__import__', 'compile'}:
                    raise ValueError(f'dynamic execution in {path.name}')
        if imports - ALLOWED_IMPORTS:
            raise ValueError(f'out-of-scope imports: {sorted(imports - ALLOWED_IMPORTS)}')
    return sorted(imports)


def coverage_ledger():
    # IDs not listed here remain Not run at L1. L1 entries name only modeled parts,
    # never OS privilege, trust authenticity, installer or native desktop proof.
    modeled = {
        3: 'abstract pause state / final-read race only',
        8: 'in-memory client framing validation only',
        9: 'injected authenticated fact, fixture capability, ID/payload/epoch checks only',
        12: 'modeled operation ownership/exclusion only',
        13: 'modeled operation ownership/exclusion only',
        14: 'single manual attempt plus legacy O/S exclusion; not two real workers',
        15: 'modeled cancellation/expiry and lock release',
        16: 'serialized fake-controller cancel/commit ordering',
        17: 'one modeled admission reader can precede commit',
        18: 'one modeled new GUI, not a real startup process',
        19: 'model exclusion and synthetic persistence ordering only',
        20: 'explicit drain-timeout transition / synthetic clock',
        21: 'fake control replay/current close authorization; no native transport ACK',
        22: 'modeled GUI exit/disconnect and supervisor ownership only',
        23: 'modeled supervisor crash releases its own leases only',
        24: 'synthetic intent-before-mutation crash boundaries; not power loss',
        25: 'in-process orphan-child state retains journal',
        26: 'abstract nonzero/postcheck-failure states; not native results',
        28: 'one legacy O/S surrogate and post-session journal recheck',
        32: 'historical receipt precedence / abstract disconnect; not protected OS receipt',
        34: 'synthetic persisted state and boot identity; not real reboot',
        35: 'in-process actor independence only; no real GUI/USB/process lifetime',
        38: 'parser chunk/frame/rate/cache bounds and one coalesced output slot; no real pipe',
        39: 'event number versus immutable Ready epoch in fake controller',
        43: 'synthetic suspend/boot/clock invalidation, not native time sources',
        44: 'modeled pause-after-read race only; remote withdrawal not modeled',
        45: 'synthetic freshness/drain/pre-intent timeout outcomes; no DNS/package probes',
        46: 'chosen synthetic durable write/journal ordering only',
    }
    return {f'F{i:02}': {'status': 'Partial L1 modeled' if i in modeled else 'Not run',
                       'scope': modeled.get(i, 'Native/integrated behavior or model not implemented'),
                       'native_status': 'Not run'} for i in range(1, 49)}



def scenario_findings():
    # Fixed public dummy credentials and IDs for an already-authenticated MODEL
    # connection. This never performs native authentication or opens an endpoint.
    attempt = "10000000-0000-0000-0000-000000000001"
    capability = "b" * 64
    def request(kind, index):
        value = dict(type=kind, id=f"20000000-0000-0000-0000-{index:012x}",
                     attempt=attempt, capability=capability)
        if kind == 'CommitInstall':
            value.update(readyEpoch=1, version='1.2.10', digest='a' * 64, installed='1.2.9')
        return value
    clock = Budget()
    commit = clock.commit(0)
    stale = clock.before_spawn(11, drained=True)
    controller = Controller(attempt, capability, authenticated=True)
    historical = controller.request(request('CommitInstall', 1))
    controller.phase = 'deferred'
    replay = controller.request(request('CommitInstall', 1), now=31)
    cache = Controller(attempt, capability, authenticated=True)
    for index in range(1, 33):
        cache.request(request('GetStatus', index), now=index)
    try:
        cache.request(request('CommitInstall', 33), now=33)
    except Rejected as exc:
        capacity_result = str(exc)
    else:
        raise AssertionError('expected conservative cache-accounting counterexample')
    assert commit == 'committed' and stale == 'deferred_stale_eligibility'
    assert historical['closeAuthorized'] and not replay['closeAuthorized']
    return [
        {'id': 'W1-C01', 'kind': 'timing counterexample',
         'observed': {'commit_at_0': commit, 'sessions_drained_at_11': stale},
         'trace': ['fresh at t=0', 'commit at t=0', 'sessions drain at t=11',
                   'safe stale deferral despite 30-second drain allowance'],
         'decision': 'D01 remains open; do not fetch network after admission or silently relax freshness'},
        {'id': 'W1-C02', 'kind': 'counterexample to naive historical ACK replay',
         'observed': {'blind_historical_close_authorized': historical['closeAuthorized'],
                      'current_state': replay['state'], 'guarded_replay_close_authorized': replay['closeAuthorized']},
         'trace': ['commit accepted', 'drain deadline => Deferred', 'repeat same Commit ID'],
         'prototype_rule': 'Idempotent effect history is not fresh close authority; recheck current committed state',
         'decision': 'Specify authoritative ACK validity after timeout before integration'},
        {'id': 'W1-C03', 'kind': 'bounded-cache usability counterexample',
         'observed': {'status_polls': 32, 'cache_entries': len(cache.cache),
                      'commit_at_second_33': capacity_result, 'effects': cache.effects},
         'decision': 'Define read-only query accounting/reserved mutation capacity; do not evict replay protection unsafely'},
        {'id': 'W1-H01', 'kind': 'harness-oracle correction',
         'detail': 'Initial oracle treated historical Updated plus a NEW legacy journal as a false protocol success. '
                   'Current decision gives that journal precedence; regression and initial development failure retained.'},
    ]


def main():
    imports = scope_review()
    suite = unittest.defaultTestLoader.discover(str(ROOT), pattern='test_harness.py')
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
    baseline = explore()
    negatives = {name: explore(name, depth=12) for name in
                 ('omit_admission', 'skip_post_session_journal', 'spawn_without_intent')}
    flush_gap = next(x for x in timeline(True) if x[0] == 'native.mutate')
    report = {
        'evidence_level': 'L1 only',
        'native_validation': False,
        'python': platform.python_version(),
        'platform': sys.platform,
        'file_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.glob('*.py'))},
        'scope_imports_checked': imports,
        'tests': {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)},
        'state_exploration': baseline,
        'negative_controls': negatives,
        'synthetic_durability': {'boundaries': len(list(timeline())),
                                 'missing_directory_flush_detected': flush_gap[2] and 'intent' not in flush_gap[1]},
        'findings': scenario_findings(),
        'fault_ledger': coverage_ledger(),
        'blockers': {f'B{i:02}': 'Unresolved; no native or integrated proof' for i in range(1, 7)},
        'limits': ['One manual attempt; two GUI actors; one legacy O/S surrogate; finite crashes/transitions.',
                   'Timeouts are explicit fair transitions in graph exploration; numerical timing checked separately.',
                   'No OS locks, processes, IPC, authentication, signatures, package installs, real power loss, or GUI tested.',
                   'Admission cannot restrain unsupported legacy clients; modeled S exclusion still applies.',
                   'Negative controls deliberately violate model rules; detected traces do not prove model completeness.'],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    ok = result.wasSuccessful() and baseline['counterexample'] is None and 'truncated' not in baseline
    ok = ok and all(value.get('counterexample') for value in negatives.values())
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
