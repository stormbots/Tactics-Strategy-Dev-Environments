"""W1 finite protocol model. No OS locks, privileges, installed paths, or IPC.

Named transitions are deterministic scheduling barriers, not elapsed sleeps.
Legacy is a surrogate for O/S-only actors, not an actual released updater.
"""
from dataclasses import dataclass, replace
from collections import deque


@dataclass(frozen=True)
class State:
    phase: str = "available"
    primary: bool = True
    peer: str = "outside"  # outside, admission, running, notice, recovery, closed
    legacy: str = "idle"  # idle, operation, sessions, journal, crashed
    operation: str = ""
    admission: bool = False
    exclusive_sessions: str = ""
    journal: str = ""
    receipt: bool = False
    native_starts: int = 0
    child: bool = False
    supervisor: bool = False
    connected: bool = True
    paused: bool = False
    pause_written: bool = False
    policy_passed: bool = False
    progress: bool = False
    entered_during_commit: bool = False


def terminal(s, phase):
    return replace(s, phase=phase, supervisor=False, operation="" if s.operation == "manual" else s.operation,
                   admission=False, exclusive_sessions="" if s.exclusive_sessions == "manual" else s.exclusive_sessions, connected=False)


def transitions(s, mutant=""):
    """All enabled transitions for one finite attempt; invalid requests change nothing."""
    out = []
    def add(name, **fields):
        out.append((name, replace(s, **fields)))
    if s.primary:
        add("gui.primary_exit", primary=False, connected=False)
    if not s.pause_written:
        add("admin.pause", paused=True, pause_written=True)
    if s.peer == "outside":
        if s.admission:
            add("gui.new_launch_blocked", peer="notice")
        elif s.journal:
            add("gui.new_launch_recovery", peer="recovery")
        else:
            add("gui.new_launch_admitted", peer="admission")
    if s.peer == "admission":
        if s.journal and mutant != "skip_post_session_journal":
            add("gui.post_session_journal_reject", peer="recovery")
        elif not s.exclusive_sessions:
            add("gui.acquire_session", peer="running",
                entered_during_commit=s.phase in {"committed", "intent", "policy", "installing", "postcheck", "recorded", "cleared"})
    if s.peer == "running":
        add("gui.secondary_exit", peer="closed")
    if s.phase == "available" and s.primary and s.connected:
        add("request.authorized", phase="authorized", supervisor=True)
    if s.phase == "authorized" and s.primary and s.connected:
        if s.paused:
            out.append(("prepare.paused", terminal(s, "paused")))
        elif s.operation:
            out.append(("prepare.busy", terminal(s, "deferred")))
        else:
            add("prepare.acquire_operation", phase="preparing", operation="manual")
    if s.phase == "preparing" and s.supervisor and s.connected:
        add("prepare.verified", phase="ready")
        out.append(("prepare.verification_failed", terminal(s, "failed")))
    if s.phase == "ready" and s.supervisor and s.connected:
        if not s.progress:
            add("status.progress_event", progress=True)
        out.append(("ready.expire", terminal(s, "canceled")))
        out.append(("ready.later", terminal(s, "canceled")))
        if s.paused:
            out.append(("commit.pause_observed", terminal(s, "paused")))
        elif s.peer != "admission":  # an in-flight admission reader must finish first
            add("commit.accept", phase="committed", admission=mutant != "omit_admission")
        else:
            out.append(("commit.admission_busy", terminal(s, "deferred")))
    if s.supervisor and s.phase in {"authorized", "preparing", "ready"} and not s.connected:
        out.append(("transport.precommit_disconnect", terminal(s, "canceled")))
    if s.phase == "committed":
        out.append(("handoff.drain_timeout", terminal(s, "deferred")))
        if not s.primary and s.peer != "running":
            add("handoff.acquire_exclusive_sessions", phase="intent", exclusive_sessions="manual")
    if s.phase == "intent" and mutant == "spawn_without_intent":
        add("native.spawn_before_intent", phase="installing", child=True, native_starts=s.native_starts + 1)
    if s.phase == "intent":
        out.append(("handoff.preintent_timeout", terminal(s, "deferred")))
        add("intent.persist", phase="policy", journal="manual")
    if s.phase == "policy":
        if s.paused:
            out.append(("intent.pause_no_spawn", terminal(replace(s, journal=""), "paused")))
        elif not s.policy_passed:
            add("intent.final_policy_read", policy_passed=True)
        if s.policy_passed:  # a subsequent pause may lose the documented final-read race
            add("native.spawn", phase="installing", child=True, native_starts=s.native_starts + 1)
    if s.phase == "installing":
        add("native.success", phase="postcheck", child=False)
        out.append(("native.failure", terminal(replace(s, child=False), "recovery")))
    if s.phase == "postcheck":
        add("postcheck.persist_complete", phase="recorded", receipt=True)
        out.append(("postcheck.failure", terminal(s, "recovery")))
    if s.phase == "recorded":
        add("journal.clear", phase="cleared", journal="")
    if s.phase == "cleared":
        out.append(("finish.release", terminal(s, "updated")))
    if s.supervisor:
        out.append(("supervisor.crash", terminal(s, "recovery" if s.journal else "canceled")))
    if s.child and not s.supervisor:
        add("native.orphan_finishes", child=False)  # never clears journal
    # One legacy attempt. Legacy ignores A, but must own O and S before intent.
    if s.legacy == "idle" and not s.operation and not s.journal:
        add("legacy.acquire_operation", legacy="operation", operation="legacy")
    if s.legacy == "operation" and not s.primary and s.peer != "running" and not s.exclusive_sessions:
        add("legacy.acquire_exclusive_sessions", legacy="sessions", exclusive_sessions="legacy")
    if s.legacy == "sessions" and not s.journal:
        add("legacy.persist_intent", legacy="journal", journal="legacy")
    if s.legacy in {"operation", "sessions", "journal"}:
        add("legacy.crash", legacy="crashed", operation="", exclusive_sessions="")
    return out


def violations(s):
    errors = []
    if s.native_starts > 1:
        errors.append("duplicate_native_effect")
    if s.child and (s.primary or s.peer == "running"):
        errors.append("native_child_overlaps_gui")
    if s.entered_during_commit:
        errors.append("new_gui_entered_committed_handoff")
    if s.phase in {"committed", "intent", "policy", "installing", "postcheck", "recorded", "cleared"}:
        if not (s.supervisor and s.operation == "manual" and s.admission):
            errors.append("committed_owner_missing")
    if s.phase in {"intent", "policy", "installing", "postcheck", "recorded", "cleared"}:
        if s.exclusive_sessions != "manual" or s.primary or s.peer == "running":
            errors.append("exclusive_session_contract")
    if s.child and not s.journal:
        errors.append("mutation_without_durable_intent")
    if s.phase == "updated" and (not s.receipt or s.journal == "manual" or s.child):
        errors.append("false_updated")
    # An existing GUI can coexist with a legacy operation journal; only a NEW
    # session admitted after uncertain intent is a startup bug. Check the edge
    # independently in edge_violations, rather than forbidding existing GUIs.
    return errors


def visible_outcome(s):
    """Current trusted intent overrides a historical successful attempt receipt."""
    if s.journal:
        return "recovery_required" if not s.supervisor else "installation_in_progress"
    if s.admission:
        return "handoff_in_progress"
    return s.phase


def edge_violations(before, event, after):
    result = violations(after)
    if event == "gui.acquire_session" and before.journal:
        result.append("startup_ignored_durable_intent")
    return result


def run_trace(events, start=None, mutant=""):
    s = start or State()
    for event in events:
        available = dict(transitions(s, mutant))
        if event not in available:
            raise ValueError(f"disabled event {event}; phase={s.phase}")
        s = available[event]
    return s


def explore(mutant="", depth=24, max_states=150000):
    """BFS with shortest counterexample. Depth/state bounds are reported honestly."""
    initial = State()
    queue = deque([(initial, 0)])
    parent = {initial: None}
    event_names = set()
    phases = {initial.phase}
    edges = 0
    depth_frontier = False
    while queue:
        before, level = queue.popleft()
        if level == depth:
            if any(after not in parent for _, after in transitions(before, mutant)):
                depth_frontier = True
            continue
        for event, after in transitions(before, mutant):
            edges += 1
            event_names.add(event)
            phases.add(after.phase)
            errors = edge_violations(before, event, after)
            if errors:
                trace = [event]
                node = before
                while parent[node] is not None:
                    previous, step = parent[node]
                    trace.append(step)
                    node = previous
                return dict(states=len(parent), edges=edges, depth_bound=depth,
                            state_limit=max_states, complete=False, counterexample=list(reversed(trace)),
                            violations=errors, phases=sorted(phases), events=sorted(event_names))
            if after not in parent:
                if len(parent) >= max_states:
                    return dict(states=len(parent), edges=edges, depth_bound=depth,
                                state_limit=max_states, complete=False, truncated="state_limit",
                                counterexample=None, phases=sorted(phases), events=sorted(event_names))
                parent[after] = (before, event)
                queue.append((after, level + 1))
    return dict(states=len(parent), edges=edges, depth_bound=depth, state_limit=max_states,
                complete=not depth_frontier, counterexample=None,
                phases=sorted(phases), events=sorted(event_names))
