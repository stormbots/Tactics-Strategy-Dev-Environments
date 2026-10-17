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
    # Public dummy credentials; native peer authentication remains injected.
    attempt = "10000000-0000-0000-0000-000000000001"
    capability = "b" * 64
    def request(kind, index):
        value = dict(type=kind, attempt=attempt, capability=capability)
        value["queryId" if kind == "GetStatus" else "commandId"] = f"20000000-0000-0000-0000-{index:012x}"
        if kind == "CommitInstall":
            value.update(readyEpoch=1, version="1.2.10", digest="a" * 64, installed="1.2.9")
        return value
    clock = Budget()
    assert clock.commit(0) == "committed"
    drained = clock.before_spawn(11)
    controller = Controller(attempt, capability, authenticated=True)
    historical = controller.request(request("CommitInstall", 1))
    controller.phase = "deferred"
    replay = controller.request(request("CommitInstall", 1), now=31)
    cache = Controller(attempt, capability, authenticated=True)
    for index in range(1, 201):
        cache.request(request("GetStatus", index), now=index)
        cache.consume_status()
    before = len(cache.cache)
    cache.budget.eligibility_at = 200  # refresh before admission
    committed = cache.request(request("CommitInstall", 201), now=201)
    assert drained == "may_write_intent"
    assert historical["closeAuthorized"] and replay["effectAccepted"] and not replay["closeAuthorized"]
    assert before == 0 and committed["closeAuthorized"] and cache.effects == 1
    return [
        {"id": "W1-C01", "status": "revision-3 local regression passed",
         "observed": {"sessions_drained_at_11": drained},
         "limit": "Synthetic acquisition/clock only; no native scheduler or network proof"},
        {"id": "W1-C02", "status": "revision-3 local regression passed",
         "observed": {"historical_effect_accepted": replay["effectAccepted"],
                      "deferred_replay_close_authorized": replay["closeAuthorized"]},
         "limit": "Injected peer/gate/clock facts; supervisor can crash after bridge validation"},
        {"id": "W1-C03", "status": "revision-3 local regression passed",
         "observed": {"status_polls": 200, "mutation_entries_before_commit": before,
                      "mutation_entries_after_commit": len(cache.cache), "effects": cache.effects},
         "limit": "Already-Ready fixture; preparation and full transport not implemented"},
        {"id": "W1-H01", "status": "historical oracle correction retained",
         "detail": "Historical Updated cannot override a newer legacy journal; regression retained."},
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
        'protocol_revision': 3,
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
