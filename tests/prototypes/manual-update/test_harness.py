import json
import struct
import unittest
from dataclasses import replace

from model import State, explore, transitions, run_trace, violations, edge_violations, visible_outcome
from framing import (Framer, Controller, FakeOutbound, Rejected, encode, decode,
                     MAX_FRAME, MAX_CHUNK, Bridge)
from durability import Store, SentinelChild, installation_decision, timeline
from timing import Budget

ATTEMPT = "10000000-0000-0000-0000-000000000001"
COMMAND = "20000000-0000-0000-0000-000000000001"
CAPABILITY = "b" * 64  # public dummy fixture, not a real authentication credential
READY = ["request.authorized", "prepare.acquire_operation", "prepare.verified"]
COMMIT = READY + ["commit.accept", "gui.primary_exit", "handoff.acquire_exclusive_sessions"]


def command(kind="CommitInstall", index=1):
    result = dict(type=kind, **{("queryId" if kind == "GetStatus" else "commandId"):f"20000000-0000-0000-0000-{index:012x}"},
                  attempt=ATTEMPT, capability=CAPABILITY)
    if kind == "CommitInstall":
        result.update(readyEpoch=1, version="1.2.10", digest="a" * 64, installed="1.2.9")
    return result


def framed_body(body):
    return struct.pack("!I", len(body)) + body


class ModelChecks(unittest.TestCase):
    def test_success_and_journal_order(self):
        s = run_trace(COMMIT + ["intent.persist", "intent.final_policy_read", "native.spawn",
                               "native.success", "postcheck.persist_complete"])
        self.assertEqual(s.phase, "recorded")
        self.assertTrue(s.journal)
        self.assertEqual(violations(s), [])
        s = run_trace(["journal.clear", "finish.release"], s)
        self.assertEqual(s.phase, "updated")
        self.assertEqual(s.native_starts, 1)
        self.assertFalse(s.admission or s.operation or s.journal)

    def test_prepare_close_cancels_without_mutation(self):
        for prefix in [READY[:1], READY[:2], READY]:
            with self.subTest(prefix=prefix):
                s = run_trace(prefix + ["gui.primary_exit", "transport.precommit_disconnect"])
                self.assertEqual(s.phase, "canceled")
                self.assertEqual(s.native_starts, 0)
                self.assertFalse(s.operation or s.admission or s.journal)

    def test_new_launch_blocked_after_commit(self):
        s = run_trace(READY + ["commit.accept", "gui.new_launch_blocked"])
        self.assertEqual(s.peer, "notice")
        self.assertFalse(s.entered_during_commit)

    def test_existing_reader_precedes_commit(self):
        s = run_trace(READY + ["gui.new_launch_admitted", "commit.admission_busy"])
        self.assertEqual(s.phase, "deferred")

    def test_existing_session_drains_or_times_out(self):
        s = run_trace(READY + ["gui.new_launch_admitted", "gui.acquire_session", "commit.accept",
                              "gui.primary_exit"])
        self.assertNotIn("handoff.acquire_exclusive_sessions", dict(transitions(s)))
        self.assertEqual(run_trace(["handoff.drain_timeout"], s).phase, "deferred")
        s = run_trace(["gui.secondary_exit", "handoff.acquire_exclusive_sessions"], s)
        self.assertEqual(s.exclusive_sessions, "manual")

    def test_old_worker_race_rechecked_after_session(self):
        steps = ["gui.primary_exit", "gui.new_launch_admitted", "legacy.acquire_operation",
                 "legacy.acquire_exclusive_sessions", "legacy.persist_intent", "legacy.crash"]
        s = run_trace(steps)
        after = run_trace(["gui.post_session_journal_reject"], s)
        self.assertEqual(after.peer, "recovery")
        bad = run_trace(["gui.acquire_session"], s, "skip_post_session_journal")
        self.assertIn("startup_ignored_durable_intent", edge_violations(s, "gui.acquire_session", bad))

    def test_helper_crash_preserves_live_child_intent(self):
        s = run_trace(COMMIT + ["intent.persist", "intent.final_policy_read", "native.spawn", "supervisor.crash"])
        self.assertTrue(s.child and s.journal)
        self.assertFalse(s.operation or s.admission)
        self.assertEqual(run_trace(["gui.new_launch_recovery"], s).peer, "recovery")
        s = run_trace(["native.orphan_finishes"], s)
        self.assertTrue(s.journal)

    def test_pause_before_read_aborts_but_after_read_can_lose_race(self):
        s = run_trace(COMMIT + ["intent.persist", "admin.pause", "intent.pause_no_spawn"])
        self.assertEqual((s.phase, s.native_starts, s.journal), ("paused", 0, ""))
        s = run_trace(COMMIT + ["intent.persist", "intent.final_policy_read", "admin.pause", "native.spawn"])
        self.assertTrue(s.paused and s.child)
        self.assertEqual(violations(s), [])

    def test_terminal_cancel_does_not_release_foreign_operation(self):
        s = run_trace(["legacy.acquire_operation", "request.authorized", "prepare.busy"])
        self.assertEqual(s.operation, "legacy")

    def test_negative_admission_control(self):
        result = explore("omit_admission", depth=10)
        self.assertIn("committed_owner_missing", result["violations"])
        self.assertIsNotNone(result["counterexample"])

    def test_negative_missing_intent_control(self):
        result = explore("spawn_without_intent", depth=12)
        self.assertIn("mutation_without_durable_intent", result["violations"])

    def test_negative_post_session_control(self):
        result = explore("skip_post_session_journal", depth=12)
        self.assertIn("startup_ignored_durable_intent", result["violations"])

    def test_historical_success_does_not_override_new_legacy_intent(self):
        s = run_trace(COMMIT + ["intent.persist", "intent.final_policy_read", "native.spawn",
                               "native.success", "postcheck.persist_complete", "journal.clear", "finish.release",
                               "legacy.acquire_operation", "legacy.acquire_exclusive_sessions", "legacy.persist_intent"])
        self.assertEqual(s.phase, "updated")  # historical manual result
        self.assertNotEqual(visible_outcome(s), "updated")
        self.assertEqual(violations(s), [])

    def test_bounded_exploration(self):
        result = explore()
        self.assertIsNone(result["counterexample"], result)
        self.assertNotIn("truncated", result)
        self.assertIn("updated", result["phases"])
        self.assertIn("native.spawn", result["events"])


class FramingChecks(unittest.TestCase):
    def test_every_split_boundary_and_bytewise(self):
        data = encode(command())
        for split in range(len(data) + 1):
            f = Framer()
            actual = f.feed(data[:split], 0) + f.feed(data[split:], 1)
            self.assertEqual(actual, [command()])
            f.eof()
        f = Framer()
        actual = []
        for b in data:
            actual += f.feed(bytes([b]), 0)
        self.assertEqual(actual, [command()])

    def test_multiple_frames_and_clean_eof(self):
        f = Framer()
        self.assertEqual(f.feed(encode(dict(type="Hello", protocol=1)) * 3, 0),
                         [dict(type="Hello", protocol=1)] * 3)
        f.eof()

    def test_all_truncated_prefixes_reject_at_eof(self):
        data = encode(command())
        for split in range(1, len(data)):
            f = Framer()
            f.feed(data[:split], 0)
            with self.assertRaises(Rejected):
                f.eof()

    def test_malformed_corpus(self):
        bad = [b'{"type":"Hello","type":"Hello","protocol":1}', b'\xff',
               b'[]', b'{"type":"Hello","protocol":true}',
               b'{"type":"Hello","protocol":2}', b'{"type":"Hello","protocol":NaN}',
               b'{"type":"Hello","protocol":1.0}', b'{"type":"Hello","protocol":9223372036854775808}',
               b'{"type":"Hello","protocol":1,"extra":0}', b'{',
               b'[' * 9 + b'0' + b']' * 9]
        for body in bad:
            with self.subTest(body=body), self.assertRaises(Rejected):
                Framer().feed(framed_body(body), 0)

    def test_unknown_fields_bad_identifiers_and_types(self):
        for key, value in [("installed", "01.2.9"), ("readyEpoch", True),
                           ("readyEpoch", 0), ("commandId", "../path"), ("digest", "x" * 64),
                           ("version", "https://attacker.invalid"), ("capability", []),
                           ("extra", "run"), ("type", "Run")]:
            with self.subTest(key=key), self.assertRaises(Rejected):
                Framer().feed(encode({**command(), key: value}), 0)

    def test_length_chunk_and_string_bounds(self):
        for size in (0, MAX_FRAME + 1, 2**32 - 1):
            with self.assertRaises(Rejected):
                Framer().feed(struct.pack("!I", size), 0)
        with self.assertRaises(Rejected):
            Framer().feed(b'x' * (MAX_CHUNK + 1), 0)
        with self.assertRaises(Rejected):
            decode(json.dumps({**command(), "version": "v" * 2049}).encode())

    def test_maximum_frame_and_seeded_malformed_traffic(self):
        import random
        body = json.dumps(dict(type="Hello", protocol=1)).encode()
        wire = framed_body(body + b' ' * (MAX_FRAME - len(body)))
        f = Framer()
        actual = []
        for at in range(0, len(wire), MAX_CHUNK):
            actual += f.feed(wire[at:at + MAX_CHUNK], 0)
        self.assertEqual(actual, [dict(type="Hello", protocol=1)])
        self.assertLessEqual(f.high_water, MAX_FRAME + 4 + MAX_CHUNK)
        rng = random.Random(72)
        for _ in range(500):
            data = bytes(rng.randrange(256) for _ in range(rng.randrange(1, 200)))
            try:
                f = Framer()
                values = f.feed(framed_body(data), 0)
            except Rejected:
                continue
            self.fail(f"random bytes unexpectedly formed a valid control: {len(values)}")

    def test_non_string_tags_and_clock_discontinuity(self):
        for value in [None, [], {}, 1, True]:
            with self.subTest(value=value), self.assertRaises(Rejected):
                Framer().feed(encode({"type": value}), 0)
        for now in [-1, float('nan'), float('inf'), True]:
            with self.subTest(now=now), self.assertRaises(Rejected):
                Framer().feed(b' ', now)
        f = Framer()
        f.feed(b'\x00', 1)
        with self.assertRaises(Rejected):
            f.feed(b'', 0)

    def test_slowloris_deadline_not_renewed(self):
        f = Framer()
        f.feed(b'\x00', 0)
        f.feed(b'\x00', 4)
        with self.assertRaises(Rejected):
            f.feed(b'\x01', 5)
        self.assertEqual(f.buffer, b'')
        with self.assertRaises(Rejected):
            f.feed(b'', 6)


class ControlChecks(unittest.TestCase):
    def controller(self):
        return Controller(ATTEMPT, CAPABILITY, authenticated=True)

    def test_authentication_is_required_even_with_fixture_capability(self):
        with self.assertRaises(Rejected):
            Controller(ATTEMPT, CAPABILITY).request(command())
        for key, value in [("attempt", "30000000-0000-0000-0000-000000000001"),
                           ("capability", "c" * 64)]:
            with self.assertRaises(Rejected):
                self.controller().request({**command(), key: value})

    def test_idempotent_commit_and_conflicting_id(self):
        c = self.controller()
        first = c.request(command())
        self.assertEqual(c.request(command()), first)
        self.assertEqual(c.effects, 1)
        with self.assertRaises(Rejected):
            c.request({**command(), "digest": "d" * 64})

    def test_cancel_commit_orderings(self):
        for first, second in [("CancelPreparation", "CommitInstall"),
                              ("CommitInstall", "CancelPreparation")]:
            c = self.controller()
            c.request(command(first))
            with self.assertRaises(Rejected):
                c.request(command(second, 2))
            self.assertEqual(c.effects, int(first == "CommitInstall"))

    def test_progress_does_not_invalidate_ready_epoch(self):
        c = self.controller()
        c.events = 50
        self.assertTrue(c.request(command())["closeAuthorized"])
        with self.assertRaises(Rejected):
            self.controller().request({**command(), "readyEpoch": 2})

    def test_late_cached_ack_cannot_close_after_defer(self):
        c = self.controller()
        old = c.request(command())
        c.phase = "deferred"  # deterministic drain deadline barrier
        replay = c.request(command(), now=1)
        self.assertTrue(old["closeAuthorized"])
        self.assertFalse(replay["closeAuthorized"])
        self.assertEqual(c.effects, 1)

    def test_queries_do_not_exhaust_mutation_slots_or_renew_deadlines(self):
        c = self.controller()
        for n in range(1, 201):
            c.request(command("GetStatus", n), now=n)
            c.consume_status()
        self.assertEqual((len(c.cache), c.events, c.budget.ready_at), (0, 0, 0))
        c.budget.eligibility_at = 200  # modeled refresh BEFORE admission
        self.assertTrue(c.request(command(index=201), now=201)["closeAuthorized"])
        self.assertEqual((len(c.cache), c.effects), (1, 1))

    def test_rate_query_and_mutation_bounds(self):
        c = self.controller()
        for i in range(1, 11):
            c.request(command("GetStatus", i))
            c.consume_status()
        with self.assertRaisesRegex(Rejected, "rate bound"):
            c.request(command("GetStatus", 11))
        self.assertEqual(c.cache, {})
        c = self.controller()
        c.request(command("GetStatus"))
        with self.assertRaisesRegex(Rejected, "query outstanding"):
            c.request(command("GetStatus", 2))
        c.consume_status()
        c.request(command())  # identical UUID, separate namespace
        for n in range(2, 100):
            with self.assertRaisesRegex(Rejected, "AlreadyAccepted"):
                c.request(command(index=n), now=n)
        self.assertEqual((len(c.cache), c.effects, c.budget.committed_at), (1, 1, 0))

    def test_replay_and_bridge_deadlines_bindings_and_terminal_order(self):
        c = self.controller()
        bridge = Bridge(c, command()["commandId"])
        ack = c.request(command())
        self.assertTrue(bridge.accepts(ack, 29.999))
        self.assertFalse(bridge.accepts(ack, 30))
        self.assertFalse(c.request(command(), now=30)["closeAuthorized"])
        for key in bridge.bindings:
            with self.subTest(key=key):
                self.assertFalse(Bridge(c, command()["commandId"]).accepts({**ack, key: "foreign"}, 1))
        for option in ({"live": False}, {"mapped": False}, {"suspended": True}):
            self.assertFalse(Bridge(c, command()["commandId"]).accepts(ack, 1, **option))
        b = Bridge(c, command()["commandId"])
        self.assertFalse(b.accepts({**ack, "state": "deferred", "eventSequence": 2}, 1))
        self.assertFalse(b.accepts(ack, 2))
        self.assertFalse(b.accepts({**ack, "eventSequence": 3}, 3))

    def test_close_requires_current_gates_and_nonterminal_state(self):
        for field in ("operation", "admission"):
            c = self.controller()
            c.request(command())
            setattr(c, field, False)
            self.assertFalse(c.request(command(), now=1)["closeAuthorized"])
        for state in ("deferred", "expired", "canceled", "recovery", "updated"):
            c = self.controller()
            c.request(command())
            c.phase = state
            ack = c.request(command(), now=1)
            self.assertTrue(ack["effectAccepted"])
            self.assertFalse(ack["closeAuthorized"])
            self.assertEqual(c.effects, 1)

    def test_rejected_flood_consumes_no_permanent_slots(self):
        c = self.controller()
        for n in range(1, 100):
            with self.assertRaises(Rejected):
                c.request({**command(index=n), "readyEpoch": 99}, now=n)
        self.assertEqual(c.cache, {})
        c.budget.eligibility_at = 100
        c.request(command(index=100), now=100)
        self.assertEqual(c.effects, 1)

    def test_status_never_grants_close_or_renews_committed_deadline(self):
        c = self.controller()
        c.request(command())
        for n in range(1, 40):
            reply = c.request(command("GetStatus", n), now=n)
            self.assertFalse(reply["closeAuthorized"])
            c.consume_status()
        self.assertEqual((c.events, c.budget.committed_at, len(c.cache)), (2, 0, 1))
        self.assertFalse(c.request(command(), now=40)["closeAuthorized"])

    def test_candidate_binding_and_client_clock_regressions(self):
        for key, value in (("digest", "c" * 64), ("version", "1.2.11"),
                           ("installed", "1.2.8")):
            with self.subTest(key=key), self.assertRaises(Rejected):
                self.controller().request({**command(), key: value})
        c = self.controller()
        ack = c.request(command())
        b = Bridge(c, command()["commandId"])
        self.assertTrue(b.accepts(ack, 2))
        self.assertFalse(b.accepts(ack, 1))
        for now in (True, float("nan"), float("inf")):
            self.assertFalse(b.accepts(ack, now))
        # The accepted grant cannot foresee a supervisor crash after validation.
        c.operation = c.admission = False
        self.assertFalse(Bridge(c, command()["commandId"]).accepts(ack, 3, live=False))

    def test_terminal_status_supersedes_pending_commit_reply(self):
        c = self.controller()
        b = Bridge(c, command()["commandId"])
        ack = c.request(command())
        status = {**ack, "correlation": command("GetStatus", 2)["queryId"],
                  "state": "deferred", "eventSequence": 2, "closeAuthorized": False}
        self.assertFalse(b.accepts(status, 1))
        self.assertFalse(b.accepts(ack, 2))

    def test_pending_status_is_current_when_consumed(self):
        c = self.controller()
        c.request(command("GetStatus"))
        c.request(command(), now=1)
        reply = c.consume_status()
        self.assertEqual((reply["state"], reply["eventSequence"]), ("committed", 1))
        self.assertFalse(reply["closeAuthorized"])

    def test_clock_uncertainty_permanently_invalidates_close_grant(self):
        c = self.controller()
        ack = c.request(command())
        for failure in ({"mapped": False}, {"suspended": True}, {"live": False}):
            b = Bridge(c, command()["commandId"])
            self.assertFalse(b.accepts(ack, 1, **failure))
            self.assertFalse(b.accepts(ack, 2))

    def test_drain_timeout_releases_fake_reservation_without_client_read(self):
        c = self.controller()
        c.request(command())
        c.tick(30)
        self.assertEqual((c.phase, c.operation, c.admission), ("deferred", False, False))
        replay = c.request(command(), now=31)
        self.assertTrue(replay["effectAccepted"])
        self.assertFalse(replay["closeAuthorized"])
        self.assertEqual(c.effects, 1)

    def test_sliding_rate_bound_crosses_second_boundary(self):
        c = self.controller()
        for n in range(1, 11):
            c.request(command("GetStatus", n), now=0.999)
            c.consume_status()
        with self.assertRaisesRegex(Rejected, "rate bound"):
            c.request(command("GetStatus", 11), now=1.0)
        c.request(command("GetStatus", 11), now=1.999)
        c.consume_status()
        self.assertEqual(c.cache, {})

    def test_progress_ordering_and_boolean_bindings(self):
        c = self.controller()
        ack = c.request(command())
        b = Bridge(c, command()["commandId"])
        self.assertFalse(b.accepts({**ack, "readyEpoch": True}, 1))
        self.assertFalse(b.accepts({**ack, "correlation": "progress", "eventSequence": 5,
                                   "closeAuthorized": False}, 2))
        self.assertFalse(b.accepts(ack, 3))
        for state in ("failed", "paused"):
            b = Bridge(c, command()["commandId"])
            b.accepts({**ack, "correlation": "status", "state": state, "eventSequence": 2}, 1)
            self.assertFalse(b.accepts({**ack, "eventSequence": 3}, 2))

    def test_non_reader_coalesces_progress_without_blocking_ticks(self):
        outbound = FakeOutbound()
        for n in range(10000):
            outbound.tick({"bytes": n})
        self.assertEqual(outbound.latest, {"bytes": 9999})
        self.assertEqual(outbound.ticks, 10000)


class DurabilityChecks(unittest.TestCase):
    def test_all_persistence_boundaries(self):
        points = list(timeline())
        for label, files, mutated, decision in points:
            with self.subTest(label=label):
                if mutated:
                    self.assertTrue(files.get("intent") == b'installing' or files.get("receipt") == b'complete')
                if 'intent' in files:
                    self.assertEqual(decision, 'recovery_required')
                if decision == 'updated':
                    self.assertEqual(files['receipt'], b'complete')
                    self.assertNotIn('intent', files)
        self.assertEqual(points[-1][-1], 'updated')

    def test_missing_intent_directory_flush_is_detected(self):
        bad = next(point for point in timeline(True) if point[0] == 'native.mutate')
        self.assertTrue(bad[2])
        self.assertNotIn('intent', bad[1])

    def test_crash_does_not_turn_unflushed_receipt_into_success(self):
        s = Store()
        s.write('receipt', b'complete')
        s.sync_directory()
        s.crash()
        self.assertNotEqual(installation_decision(s), 'updated')

    def test_fake_child_fixed_temporary_sentinel(self):
        child = SentinelChild()
        root = child.root
        try:
            child.start()
            with self.assertRaises(ValueError):
                child.start()
            child.finish()
            self.assertEqual((root / 'PROTOTYPE-NATIVE-SENTINEL').read_text(), 'finished\n')
        finally:
            child.close()
        self.assertFalse(root.exists())


class TimingChecks(unittest.TestCase):
    def test_freshness_at_acquisition_and_drain_boundaries(self):
        for at, result in ((10, "committed"), (10.001, "refresh_before_admission")):
            self.assertEqual(Budget().commit(at), result)
        for at, result in ((11, "may_write_intent"), (29.999, "may_write_intent"), (30, "deferred")):
            b = Budget()
            b.commit(0)
            self.assertEqual(b.before_spawn(at), result)

    def test_durable_work_included_in_final_launch_deadline(self):
        for at, result in ((44.999, "may_spawn"), (45, "retain_uncertain_intent")):
            b = Budget()
            b.commit(10)
            b.before_spawn(39.999)  # drained <30 seconds from A
            b.intent = True
            self.assertEqual(b.before_spawn(10 + at), result)
            self.assertTrue(b.intent)
        b = Budget()
        b.commit(0)
        b.before_spawn(1)
        self.assertEqual(b.before_spawn(45), "deferred")

    def test_retries_do_not_renew_and_local_checks_still_apply(self):
        b = Budget()
        b.commit(0)
        self.assertEqual(b.commit(1), "already_committed")
        self.assertEqual(b.committed_at, 0)
        for kwargs in ({"paused": True}, {"integrity": False}):
            b = Budget()
            b.commit(0)
            self.assertEqual(b.before_spawn(1, **kwargs), "deferred")
            b.intent = True
            self.assertEqual(b.before_spawn(2, **kwargs), "retain_uncertain_intent")

    def test_deferred_attempt_cannot_resume_after_checks_recover(self):
        for kwargs in ({"paused": True}, {"integrity": False}, {"boot": "other"}):
            b = Budget()
            b.commit(0)
            self.assertEqual(b.before_spawn(1, **kwargs), "deferred")
            self.assertEqual(b.before_spawn(2), "deferred")
            self.assertEqual(b.commit(2), "expired")
        b = Budget()
        self.assertEqual(b.commit(1, boot="other"), "expired")
        self.assertEqual(b.commit(2), "expired")

    def test_suspend_reboot_and_clock_discontinuity(self):
        self.assertEqual(Budget(suspended=True).commit(1), "expired")
        self.assertEqual(Budget().commit(1, boot="new-boot"), "expired")
        self.assertEqual(Budget().commit(300), "expired")
        for now in (-1, float("nan"), float("inf"), True):
            self.assertEqual(Budget().commit(now), "expired")
        for kwargs in ({"boot": "new-boot"}, {}):
            b = Budget()
            b.commit(2)
            self.assertEqual(b.before_spawn(1, **kwargs), "deferred")
        b = Budget()
        b.commit(0)
        b.suspended = True
        self.assertEqual(b.before_spawn(1), "deferred")


if __name__ == '__main__':
    unittest.main()
