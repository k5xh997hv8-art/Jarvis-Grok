"""Intent Ledger v0.2: a model proposes, a human decides, the record stays honest.

Standard library only. Python 3.9 or newer.

The rules, enforced in code:
  1. Nothing is written to the ledger without an explicit human approve().
     There is no auto-approve switch, no default yes and no timeout.
  2. A veto is final. The proposal leaves the queue and nothing is written.
  3. Proposals wait in an ordered queue (first in, first out), as many as needed.
  4. A proposal that sounds like an overclaim is held. It cannot be approved
     by accident. The human must approve it on purpose or veto it.
  5. The ledger is append-only and hash-chained. verify() catches any edit,
     insertion, reordering or removal, and every read verifies first.

Files in the ledger folder:
  owner.key     the human's local secret (never leaves this computer)
  pending.json  the queue of proposals (not part of the record)
  ledger.jsonl  approved entries, one JSON object per line, hash-chained
  head.json     sealed checkpoint of the latest entry (catches cut-off endings)

Fixes the 26 to 28 Jul 2026 prototype: auto_approve=True by default, a
single-slot pending veto, vetoes written as records without approval, and
no tests. Same design as XiCore v0.1 (xicore-pkg), which adds Ed25519 keys.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import tempfile
from datetime import datetime, timezone

VERSION = 1
GENESIS = "0" * 64
ENTRY_PREFIX = "intent-ledger/entry/v1\n"
HEAD_PREFIX = "intent-ledger/head/v1\n"
ENTRY_FIELDS = ("v", "i", "prev", "id", "kind", "text", "source",
                "proposedAt", "decidedAt", "decision", "held")
MAX_TEXT = 4000

# Words that make a line read like a status claim or an official link.
# Matching items are held for a deliberate human decision.
DEFAULT_HOLD_TERMS = (
    r"online", r"live", r"official(ly)?", r"affiliated", r"endorsed",
    r"guaranteed", r"proven", r"100\s*%", r"sentient", r"conscious",
    r"fully autonomous", r"integrated into grok",
)


class LedgerError(Exception):
    """Base error."""


class NotPending(LedgerError):
    """The id is not in the queue (never proposed, already approved, or vetoed)."""


class HeldForReview(LedgerError):
    """The proposal is flagged. Approve with accept_hold=True or veto it."""


class TamperError(LedgerError):
    """The ledger failed verification. Nothing is returned from it."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _stable(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_atomic(path: str, text: str) -> None:
    folder = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def entry_hash(entry: dict) -> str:
    return _sha256(ENTRY_PREFIX + _stable({k: entry.get(k) for k in ENTRY_FIELDS}))


class IntentLedger:
    def __init__(self, home: str, hold_terms=DEFAULT_HOLD_TERMS):
        self.home = os.path.abspath(home)
        os.makedirs(self.home, mode=0o700, exist_ok=True)
        self._key_path = os.path.join(self.home, "owner.key")
        self._pending_path = os.path.join(self.home, "pending.json")
        self._ledger_path = os.path.join(self.home, "ledger.jsonl")
        self._head_path = os.path.join(self.home, "head.json")
        self._hold = [re.compile(r"\b" + t + r"\b", re.IGNORECASE) for t in hold_terms]
        self._key = self._load_or_make_key()

    # ---------- key ----------
    def _load_or_make_key(self) -> bytes:
        if not os.path.exists(self._key_path):
            fd = os.open(self._key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_hex(32))
        with open(self._key_path, encoding="ascii") as f:
            return bytes.fromhex(f.read().strip())

    def _seal(self, text: str) -> str:
        return hmac.new(self._key, text.encode("utf-8"), hashlib.sha256).hexdigest()

    # ---------- queue ----------
    def _read_queue(self) -> dict:
        if not os.path.exists(self._pending_path):
            return {"next_seq": 1, "items": []}
        with open(self._pending_path, encoding="utf-8") as f:
            return json.load(f)

    def _save_queue(self, q: dict) -> None:
        _write_atomic(self._pending_path, json.dumps(q, indent=2, ensure_ascii=False) + "\n")

    def hold_reasons(self, text: str) -> list:
        return sorted({m.group(0).lower() for rx in self._hold for m in [rx.search(text)] if m})

    def propose(self, text: str, source: str = "model", kind: str = "intent") -> dict:
        """Add a proposal to the end of the queue. Never writes to the ledger."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("a proposal needs some text")
        if len(text) > MAX_TEXT:
            raise ValueError(f"a proposal is limited to {MAX_TEXT} characters")
        q = self._read_queue()
        item = {
            "seq": q["next_seq"],
            "id": secrets.token_hex(6),
            "text": text.strip(),
            "kind": str(kind),
            "source": str(source),
            "proposedAt": _now(),
            "held": self.hold_reasons(text),
        }
        q["next_seq"] += 1
        q["items"].append(item)
        self._save_queue(q)
        return dict(item)

    def pending(self) -> list:
        """The queue, oldest first."""
        return sorted(self._read_queue()["items"], key=lambda it: it["seq"])

    def _take(self, item_id: str):
        q = self._read_queue()
        for n, it in enumerate(q["items"]):
            if it["id"] == item_id:
                return q, n, it
        raise NotPending(f"{item_id} is not waiting for a decision")

    def veto(self, item_id: str) -> None:
        """Final. The proposal leaves the queue and nothing is written."""
        q, n, _ = self._take(item_id)
        del q["items"][n]
        self._save_queue(q)

    def approve(self, item_id: str, accept_hold: bool = False) -> dict:
        """The only way anything reaches the ledger."""
        q, n, item = self._take(item_id)
        if item["held"] and not accept_hold:
            raise HeldForReview(
                f"{item_id} is held ({', '.join(item['held'])}). "
                "Approve it on purpose (accept_hold=True, or --accept-hold on the command line), or veto it.")
        entries = self.entries()  # verifies first, refuses on tamper
        entry = {
            "v": VERSION,
            "i": len(entries),
            "prev": entries[-1]["hash"] if entries else GENESIS,
            "id": item["id"],
            "kind": item["kind"],
            "text": item["text"],
            "source": item["source"],
            "proposedAt": item["proposedAt"],
            "decidedAt": _now(),
            "decision": "approved",
            "held": item["held"],
        }
        entry["hash"] = entry_hash(entry)
        entry["seal"] = self._seal(entry["hash"])
        with open(self._ledger_path, "a", encoding="utf-8") as f:
            f.write(_stable(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
        head = {"count": entry["i"] + 1, "head": entry["hash"]}
        head["seal"] = self._seal(HEAD_PREFIX + _stable(head))
        _write_atomic(self._head_path, _stable(head) + "\n")
        del q["items"][n]
        self._save_queue(q)
        return dict(entry)

    # ---------- ledger ----------
    def _raw_entries(self) -> list:
        if not os.path.exists(self._ledger_path):
            return []
        out = []
        with open(self._ledger_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    out.append(json.loads(line))
        return out

    def verify(self) -> list:
        """Return a list of problems. An empty list means the ledger is intact."""
        problems = []
        try:
            entries = self._raw_entries()
        except (ValueError, OSError) as e:
            return [f"ledger file unreadable: {e}"]
        prev = GENESIS
        for n, e in enumerate(entries):
            if not isinstance(e, dict):
                problems.append(f"line {n + 1}: not an entry")
                continue
            if e.get("i") != n:
                problems.append(f"line {n + 1}: position is {e.get('i')}, expected {n}")
            if e.get("prev") != prev:
                problems.append(f"line {n + 1}: does not link to the entry before it")
            if e.get("decision") != "approved":
                problems.append(f"line {n + 1}: not an approved entry")
            h = entry_hash(e)
            if e.get("hash") != h:
                problems.append(f"line {n + 1}: contents changed after approval")
            if not hmac.compare_digest(str(e.get("seal", "")), self._seal(h)):
                problems.append(f"line {n + 1}: approval seal does not match the owner key")
            prev = e.get("hash")
        if os.path.exists(self._head_path):
            try:
                with open(self._head_path, encoding="utf-8") as f:
                    head = json.load(f)
            except ValueError:
                head = {}
            body = {"count": head.get("count"), "head": head.get("head")}
            if not hmac.compare_digest(str(head.get("seal", "")),
                                       self._seal(HEAD_PREFIX + _stable(body))):
                problems.append("checkpoint seal does not match the owner key")
            if body["count"] != len(entries) or body["head"] != (entries[-1].get("hash") if entries else None):
                problems.append(f"checkpoint says {body['count']} entries, ledger has {len(entries)}")
        elif entries:
            problems.append("checkpoint missing")
        return problems

    def entries(self) -> list:
        """Approved entries, oldest first. Verifies first and refuses on tamper."""
        problems = self.verify()
        if problems:
            raise TamperError("; ".join(problems))
        return self._raw_entries()


# ---------- command line ----------
USAGE = """usage: python3 intent_ledger.py [--home DIR] COMMAND
  propose "text"            add to the queue (never writes to the ledger)
  pending                   show the queue, oldest first
  approve ID [--accept-hold]  write it to the ledger (held items need --accept-hold)
  veto ID                   final: remove it, nothing is written
  log                       show approved entries (verifies first)
  verify                    check the whole chain; exit code 2 on tamper
The folder defaults to $INTENT_LEDGER_HOME or ./ledger-data"""


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    home = os.environ.get("INTENT_LEDGER_HOME", "ledger-data")
    if args[:1] == ["--home"] and len(args) >= 2:
        home, args = args[1], args[2:]
    if not args:
        print(USAGE)
        return 1
    led = IntentLedger(home)
    cmd, rest = args[0], args[1:]
    try:
        if cmd == "propose" and rest:
            it = led.propose(" ".join(rest), source="cli")
            note = f"  HELD: {', '.join(it['held'])}" if it["held"] else ""
            print(f"queued {it['id']}{note}")
        elif cmd == "pending":
            for it in led.pending():
                note = f"  [HELD: {', '.join(it['held'])}]" if it["held"] else ""
                print(f"{it['seq']:>3}  {it['id']}  {it['text']}{note}")
        elif cmd == "approve" and rest:
            e = led.approve(rest[0], accept_hold="--accept-hold" in rest)
            print(f"approved {e['id']} as entry {e['i']}")
        elif cmd == "veto" and rest:
            led.veto(rest[0])
            print(f"vetoed {rest[0]}. Nothing written.")
        elif cmd == "log":
            for e in led.entries():
                print(f"{e['i']:>3}  {e['decidedAt'][:19]}  {e['text']}")
        elif cmd == "verify":
            problems = led.verify()
            if problems:
                print("TAMPER")
                for p in problems:
                    print("  " + p)
                return 2
            print(f"OK: {len(led._raw_entries())} entries, chain intact")
        else:
            print(USAGE)
            return 1
    except TamperError as e:
        print(f"TAMPER: {e}")
        return 2
    except LedgerError as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
