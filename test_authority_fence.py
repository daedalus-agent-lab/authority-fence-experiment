#!/usr/bin/env python3
"""Invariant tests for authority_fence.py — stdlib unittest, no network."""

import threading
import unittest

from authority_fence import (Store, ReadOnlyObserver, arm_a_unfenced,
                             arm_b_fenced, arm_c_observer, arm_d_key_seal,
                             fuzz_fence)


class TestInvariants(unittest.TestCase):

    # I1 — epoch never goes backwards
    def test_epoch_monotonic(self):
        s = Store()
        seen = []
        for _ in range(5):
            seen.append(s.grant("x").epoch)
            seen.append(s.revoke("x")["new_epoch"])
        self.assertEqual(seen, sorted(seen))
        self.assertEqual(len(set(seen)), len(seen))

    # I3 — at most one APPLIED per (subject, request_key)
    def test_idempotent_replay_does_not_duplicate_effect(self):
        s = Store()
        a = s.grant("x")
        r1 = s.apply_effect(a, "k")
        r2 = s.apply_effect(a, "k")
        self.assertEqual(r1["decision"], "APPLIED")
        self.assertEqual(r2["decision"], "APPLIED")
        self.assertTrue(r2["replay"])
        self.assertEqual(s.effects, ["k"])
        applied = [e for e in s.log if e.kind == "APPLIED"]
        self.assertEqual(len(applied), 1)

    # I3 — request keys are scoped by subject, not globally shared
    def test_same_request_key_can_be_used_by_another_subject(self):
        s = Store()
        ax = s.grant("x")
        ay = s.grant("y")
        rx = s.apply_effect(ax, "shared-key")
        ry = s.apply_effect(ay, "shared-key")
        self.assertEqual(rx["decision"], "APPLIED")
        self.assertEqual(ry["decision"], "APPLIED")
        self.assertFalse(ry["replay"])
        self.assertEqual(s.effects, ["shared-key", "shared-key"])
        applied = [e for e in s.log if e.kind == "APPLIED"]
        self.assertEqual([(e.subject, e.request_key) for e in applied],
                         [("x", "shared-key"), ("y", "shared-key")])

    # I4 — only the admission path issues a witness; a reader cannot mint one
    def test_reader_cannot_issue_not_applied(self):
        s = Store()
        s.grant("x")
        obs = ReadOnlyObserver(s)
        out = obs.honest_conclusion("x", "k")
        self.assertEqual(out["decision"], "UNKNOWN")
        self.assertFalse(out["permit_retry"])
        self.assertTrue(out["issued_by"].startswith("reader:"))
        self.assertNotIn("position", out)   # no log position => not a witness

    def test_store_witness_names_a_position(self):
        s = Store()
        a = s.grant("x")
        s.revoke("x")
        w = s.apply_effect(a, "k")
        self.assertEqual(w["decision"], "NOT_APPLIED")
        self.assertEqual(w["issued_by"], "store:admission")
        self.assertIn("log_index", w["position"])
        self.assertTrue(w["permit_retry"])
        self.assertIn("exactly-once end to end", w["does_not_claim"])
        self.assertIn("that this request_key is sealed or reserved", w["does_not_claim"])
        self.assertEqual(
            w["binding"],
            "refused_at_this_store_for_this_subject_and_presented_epoch",
        )

    def test_refusal_does_not_seal_key_and_is_epoch_scoped(self):
        s = Store()
        old = s.grant("x")
        s.revoke("x")
        witness = s.apply_effect(old, "k")
        fresh = s.grant("x")
        applied = s.apply_effect(fresh, "k")
        self.assertEqual(witness["decision"], "NOT_APPLIED")
        self.assertEqual(applied["decision"], "APPLIED")
        self.assertFalse(applied["replay"])
        self.assertEqual(s.effects, ["k"])

    # I5 — under the fence, no APPLIED entry survives a preceding REVOKE
    def test_no_admission_after_revocation(self):
        s = Store(enforce_fence=True)
        a = s.grant("x")
        s.revoke("x")
        w = s.apply_effect(a, "k")
        self.assertEqual(w["decision"], "NOT_APPLIED")
        self.assertEqual(s.effects, [])

    # the hash chain actually chains
    def test_log_hash_chain_links(self):
        s = Store()
        a = s.grant("x")
        s.apply_effect(a, "k")
        s.revoke("x")
        prev = "0" * 64
        for e in s.log:
            self.assertEqual(e.prev_head, prev)
            prev = e.head


class TestArms(unittest.TestCase):

    def test_arm_a_delayed_apply_succeeds_despite_valid_read(self):
        r = arm_a_unfenced()
        self.assertTrue(r["read_at_t0"]["valid_now"])          # read said VALID
        self.assertEqual(r["apply_receipt"]["decision"], "APPLIED")
        self.assertGreater(r["apply_receipt"]["position"]["log_index"],
                           r["revocation"]["revoked_at_index"])

    def test_arm_b_same_read_opposite_outcome(self):
        r = arm_b_fenced()
        self.assertTrue(r["read_at_t0"]["valid_now"])
        self.assertEqual(r["witness"]["decision"], "NOT_APPLIED")
        self.assertEqual(r["effects"], [])

    def test_arm_c_absence_inference_is_falsified(self):
        r = arm_c_observer()
        self.assertEqual(r["naive_conclusion_before_apply"]["decision"], "NOT_APPLIED")
        self.assertEqual(r["late_apply_receipt"]["decision"], "APPLIED")
        self.assertTrue(r["falsified"])
        self.assertEqual(r["honest_conclusion_before_apply"]["decision"], "UNKNOWN")
        self.assertEqual(r["honest_conclusion_after_apply"]["decision"], "APPLIED")

    def test_arm_d_epoch_refusal_is_not_a_key_seal(self):
        """just-nik's falsifier: CLOSED(K)@F is not a rename of the refusal."""
        r = arm_d_key_seal()
        self.assertEqual(r["refusal_under_stale_epoch"]["decision"], "NOT_APPLIED")
        self.assertEqual(r["second_apply_same_key_fresh_epoch"]["decision"], "APPLIED")
        self.assertFalse(r["second_apply_same_key_fresh_epoch"]["replay"])
        self.assertTrue(r["key_seal_claim_falsified"])
        # one REFUSED row and one APPLIED row under the same key: two receipts
        kinds = [e["kind"] for e in r["log"] if e["request_key"] == "req-K"]
        self.assertEqual(kinds, ["REFUSED", "APPLIED"])
        self.assertEqual(r["effects"], ["req-K"])


class TestControls(unittest.TestCase):

    def test_correct_fence_holds_under_fuzz(self):
        self.assertTrue(fuzz_fence(120, broken=False)["pass"])

    def test_broken_fence_is_caught(self):
        """A harness that cannot fail proves nothing."""
        r = fuzz_fence(120, broken=True)
        self.assertGreater(r["applied_after_revoke"], 0)
        self.assertTrue(r["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
