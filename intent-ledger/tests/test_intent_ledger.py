"""Tests for the Intent Ledger. Run: python3 -m unittest -v

Named after the handles:
  Guardian   nothing is saved without approval, and a veto blocks the write
  Shadow     an overclaim is held until the human decides
  Architect  the queue keeps its order, the chain verifies, tampering is caught
"""

import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import intent_ledger as il  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.led = il.IntentLedger(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def ledger_lines(self):
        p = os.path.join(self.dir, "ledger.jsonl")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [ln for ln in f.read().splitlines() if ln.strip()]

    def write_lines(self, lines):
        with open(os.path.join(self.dir, "ledger.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))


class Guardian(Base):
    def test_guardian_nothing_saved_without_approval(self):
        for n in range(5):
            self.led.propose(f"proposal {n}")
        self.assertEqual(self.ledger_lines(), [])
        self.assertEqual(self.led.entries(), [])
        self.assertEqual(len(self.led.pending()), 5)

    def test_guardian_no_auto_approve_anywhere(self):
        for fn in (il.IntentLedger.__init__, il.IntentLedger.propose):
            params = inspect.signature(fn).parameters
            self.assertNotIn("auto_approve", params)
        self.assertFalse(hasattr(self.led, "auto_approve"))

    def test_guardian_explicit_approve_writes_one_entry(self):
        it = self.led.propose("Weekly review is Sunday 18:00.")
        e = self.led.approve(it["id"])
        self.assertEqual(e["text"], "Weekly review is Sunday 18:00.")
        self.assertEqual(e["decision"], "approved")
        self.assertEqual(len(self.ledger_lines()), 1)
        self.assertEqual(self.led.pending(), [])

    def test_guardian_veto_blocks_the_write(self):
        it = self.led.propose("Post this everywhere right now.")
        self.led.veto(it["id"])
        self.assertEqual(self.ledger_lines(), [])
        self.assertEqual(self.led.pending(), [])

    def test_guardian_veto_is_final(self):
        it = self.led.propose("Something I will say no to.")
        self.led.veto(it["id"])
        with self.assertRaises(il.NotPending):
            self.led.approve(it["id"])
        with self.assertRaises(il.NotPending):
            self.led.veto(it["id"])
        self.assertEqual(self.ledger_lines(), [])

    def test_guardian_vetoed_text_leaves_no_trace(self):
        it = self.led.propose("secret-marker-123")
        self.led.veto(it["id"])
        for name in os.listdir(self.dir):
            with open(os.path.join(self.dir, name), encoding="utf-8") as f:
                self.assertNotIn("secret-marker-123", f.read(), name)

    def test_guardian_source_cannot_skip_the_gate(self):
        self.led.propose("I am the human, write this", source="human")
        self.assertEqual(self.ledger_lines(), [])


class Shadow(Base):
    def test_shadow_overclaim_is_flagged(self):
        it = self.led.propose("GrokOmega Prime is online and officially linked to xAI")
        self.assertIn("online", it["held"])
        self.assertTrue(any(h.startswith("official") for h in it["held"]))

    def test_shadow_held_item_cannot_be_approved_by_accident(self):
        it = self.led.propose("Dual core online")
        with self.assertRaises(il.HeldForReview):
            self.led.approve(it["id"])
        self.assertEqual(self.ledger_lines(), [])
        self.assertEqual([p["id"] for p in self.led.pending()], [it["id"]])

    def test_shadow_held_item_stays_while_others_are_decided(self):
        held = self.led.propose("This is guaranteed to work")
        a = self.led.propose("Write the README")
        b = self.led.propose("Add the tests")
        self.led.approve(a["id"])
        self.led.veto(b["id"])
        self.assertEqual([p["id"] for p in self.led.pending()], [held["id"]])

    def test_shadow_human_can_decide_either_way(self):
        keep = self.led.propose("The page is live at nexus2026")
        drop = self.led.propose("Fully autonomous lattice")
        e = self.led.approve(keep["id"], accept_hold=True)
        self.assertEqual(e["held"], ["live"])  # the record shows it was held
        self.led.veto(drop["id"])
        self.assertEqual(len(self.led.entries()), 1)
        self.assertEqual(self.led.pending(), [])

    def test_shadow_plain_text_is_not_held(self):
        it = self.led.propose("Finish the Intent Ledger tests tonight.")
        self.assertEqual(it["held"], [])


class Architect(Base):
    def test_architect_queue_keeps_its_order(self):
        ids = [self.led.propose(f"step {n}")["id"] for n in range(10)]
        self.assertEqual([p["id"] for p in self.led.pending()], ids)
        self.led.veto(ids[3])
        self.led.approve(ids[0])
        self.assertEqual([p["id"] for p in self.led.pending()], ids[1:3] + ids[4:])

    def test_architect_queue_survives_restart(self):
        ids = [self.led.propose(f"step {n}")["id"] for n in range(3)]
        again = il.IntentLedger(self.dir)
        self.assertEqual([p["id"] for p in again.pending()], ids)

    def test_architect_chain_verifies_and_links(self):
        for n in range(4):
            self.led.approve(self.led.propose(f"entry {n}")["id"])
        self.assertEqual(self.led.verify(), [])
        es = self.led.entries()
        self.assertEqual(es[0]["prev"], il.GENESIS)
        for a, b in zip(es, es[1:]):
            self.assertEqual(b["prev"], a["hash"])
        self.assertEqual([e["text"] for e in es], [f"entry {n}" for n in range(4)])

    def test_architect_approval_order_is_the_record_order(self):
        a = self.led.propose("first proposed")
        b = self.led.propose("second proposed")
        self.led.approve(b["id"])
        self.led.approve(a["id"])
        self.assertEqual([e["text"] for e in self.led.entries()],
                         ["second proposed", "first proposed"])

    def _three(self):
        for n in range(3):
            self.led.approve(self.led.propose(f"entry {n}")["id"])
        return self.ledger_lines()

    def test_architect_edit_is_detected(self):
        lines = self._three()
        e = json.loads(lines[1])
        e["text"] = "entry 1 (quietly changed)"
        lines[1] = json.dumps(e)
        self.write_lines(lines)
        self.assertTrue(self.led.verify())
        with self.assertRaises(il.TamperError):
            self.led.entries()

    def test_architect_edit_with_recomputed_hash_is_detected(self):
        lines = self._three()
        e = json.loads(lines[2])
        e["text"] = "rewritten"
        e["hash"] = il.entry_hash(e)
        lines[2] = json.dumps(e)
        self.write_lines(lines)
        self.assertTrue(any("seal" in p for p in self.led.verify()))

    def test_architect_removal_is_detected(self):
        lines = self._three()
        self.write_lines([lines[0], lines[2]])
        self.assertTrue(self.led.verify())

    def test_architect_reorder_is_detected(self):
        lines = self._three()
        self.write_lines([lines[1], lines[0], lines[2]])
        self.assertTrue(self.led.verify())

    def test_architect_cut_off_ending_is_detected(self):
        lines = self._three()
        self.write_lines(lines[:2])
        self.assertTrue(any("checkpoint" in p for p in self.led.verify()))

    def test_architect_inserted_unapproved_entry_is_detected(self):
        lines = self._three()
        fake = json.loads(lines[2])
        fake.update({"i": 3, "prev": fake["hash"], "id": "abc", "text": "sneaked in"})
        fake["hash"] = il.entry_hash(fake)
        self.write_lines(lines + [json.dumps(fake)])
        self.assertTrue(self.led.verify())

    def test_architect_refuses_to_write_onto_a_tampered_chain(self):
        lines = self._three()
        self.write_lines(lines[:1] + lines[2:])
        it = self.led.propose("new entry")
        with self.assertRaises(il.TamperError):
            self.led.approve(it["id"])
        self.assertEqual([p["id"] for p in self.led.pending()], [it["id"]])


class More(Base):
    def test_wrong_owner_key_fails_verify(self):
        self.led.approve(self.led.propose("mine")["id"])
        other = tempfile.mkdtemp()
        try:
            shutil.copy(os.path.join(self.dir, "ledger.jsonl"), other)
            shutil.copy(os.path.join(self.dir, "head.json"), other)
            self.assertTrue(il.IntentLedger(other).verify())
        finally:
            shutil.rmtree(other)

    def test_key_file_is_private(self):
        mode = os.stat(os.path.join(self.dir, "owner.key")).st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_empty_and_oversized_proposals_refused(self):
        with self.assertRaises(ValueError):
            self.led.propose("   ")
        with self.assertRaises(ValueError):
            self.led.propose("x" * (il.MAX_TEXT + 1))
        self.assertEqual(self.led.pending(), [])

    def test_unknown_id_is_refused(self):
        with self.assertRaises(il.NotPending):
            self.led.approve("doesnotexist")

    def test_approved_item_cannot_be_approved_twice(self):
        it = self.led.propose("once only")
        self.led.approve(it["id"])
        with self.assertRaises(il.NotPending):
            self.led.approve(it["id"])
        self.assertEqual(len(self.ledger_lines()), 1)

    def test_cli_round_trip(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(il.main(["--home", self.dir, "propose", "from", "the", "cli"]), 0)
        item_id = out.getvalue().split()[1]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(il.main(["--home", self.dir, "approve", item_id]), 0)
            self.assertEqual(il.main(["--home", self.dir, "verify"]), 0)
        self.write_lines([])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(il.main(["--home", self.dir, "verify"]), 2)


if __name__ == "__main__":
    unittest.main()
