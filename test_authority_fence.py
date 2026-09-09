#!/usr/bin/env python3
"""Invariant tests for authority_fence.py — stdlib unittest, no network."""

import threading
import unittest

from authority_fence import (Store, ReadOnlyObserver, arm_a_unfenced,
                             arm_b_fenced, arm_c_observer, fuzz_fence)


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
