# Intent Ledger

**A model can suggest. Only you can say yes. The record can't be quietly changed.**

The Intent Ledger is a small Python tool that sits between an AI model and your permanent record.

1. **Propose.** The model (or anything else) adds suggestions to a waiting list. Nothing is saved yet.
2. **Decide.** You approve or veto each one. A veto is final: the suggestion is deleted and never written.
3. **Record.** Only approved items go into the ledger. Each entry is linked to the one before it by a fingerprint (a SHA-256 hash), so any later edit, removal or reshuffle is caught.

If a suggestion sounds like an overclaim ("online", "official", "guaranteed" and similar), it is **held**. A normal approve won't accept it. You have to approve it on purpose or veto it.

## Try it (two commands)

Needs Python 3.9 or newer. Nothing to install.

```bash
python3 example.py              # one-minute walk through
python3 -m unittest -v          # run the 29 tests
```

## Use it

```bash
python3 intent_ledger.py propose "Weekly review every Sunday at 18:00."
python3 intent_ledger.py pending          # the waiting list, oldest first
python3 intent_ledger.py approve <id>     # the only way anything is saved
python3 intent_ledger.py veto <id>        # final, nothing is written
python3 intent_ledger.py log              # what you approved
python3 intent_ledger.py verify           # checks the whole chain
```

Or from Python:

```python
from intent_ledger import IntentLedger
ledger = IntentLedger("my-ledger")
item = ledger.propose("Weekly review every Sunday at 18:00.")
ledger.approve(item["id"])     # or ledger.veto(item["id"])
print(ledger.entries())        # checks the chain first, refuses if tampered
```

## The three tests that matter

| Handle | What it proves |
| --- | --- |
| **Guardian** | Nothing is saved without your approve. A veto blocks the write and leaves no trace. There is no auto-approve setting at all. |
| **Shadow** | An overclaim is held. It can't slip through with a normal approve, and it waits until you decide. |
| **Architect** | The waiting list keeps its order. The chain checks out. Edits, removals, reordering, a cut-off ending or a sneaked-in entry are all caught. |

## Files it keeps (in the ledger folder)

- `owner.key` your local secret, readable only by you. It seals each approval.
- `pending.json` the waiting list. Not part of the record.
- `ledger.jsonl` approved entries, one per line, hash-linked.
- `head.json` a sealed note of the latest entry, so a cut-off ending is caught.

## Honest limits

- It's a local tool for one person. No sync, no server, nothing runs on its own.
- Seals use a secret key (HMAC). That proves the key holder approved, but anyone checking needs the same key. XiCore v0.1 uses public-key signatures (Ed25519) for that.
- Someone with full access to your computer could still delete the whole folder or roll everything back to an older copy. Keep a backup somewhere else.
- The overclaim word list is simple and can be changed. It flags words, it doesn't understand meaning.

## Where it came from

A model-proposes, human-approves loop first written with Grok on 26 to 28 Jul 2026. That version approved everything by default, held only one item at a time, wrote vetoes into the record without approval, and had no tests. This version fixes all four.

Independent personal project by Tommy Maloney, built with Grok. Not affiliated with xAI.
