"""A one-minute walk through the Intent Ledger. Run: python3 example.py

Uses a throwaway folder, so nothing is kept afterwards.
"""

import json
import os
import shutil
import tempfile

from intent_ledger import HeldForReview, IntentLedger

folder = tempfile.mkdtemp(prefix="intent-ledger-demo-")
ledger = IntentLedger(folder)

print("1. A model proposes three things. Nothing is written yet.")
a = ledger.propose("Weekly review every Sunday at 18:00.")
b = ledger.propose("Post the draft to every channel right now.")
c = ledger.propose("The system is online and officially linked to xAI.")
for item in ledger.pending():
    note = f"   <- HELD: {', '.join(item['held'])}" if item["held"] else ""
    print(f"   {item['seq']}. {item['text']}{note}")
print(f"   Entries in the ledger: {len(ledger.entries())}")

print("\n2. The human decides.")
ledger.approve(a["id"])
print("   Approved: weekly review.")
ledger.veto(b["id"])
print("   Vetoed: the post. It is gone and nothing was written.")
try:
    ledger.approve(c["id"])
except HeldForReview:
    print("   Tried a plain approve on the overclaim: refused, it stays held.")
ledger.veto(c["id"])
print("   Vetoed the overclaim on purpose.")

print("\n3. The record.")
for e in ledger.entries():
    print(f"   #{e['i']} {e['text']}  (hash {e['hash'][:12]}...)")
print(f"   Still waiting: {len(ledger.pending())}")
print(f"   Verify: {'intact' if not ledger.verify() else ledger.verify()}")

print("\n4. Someone quietly edits the record.")
path = os.path.join(folder, "ledger.jsonl")
with open(path) as f:
    entry = json.loads(f.readline())
entry["text"] = "Weekly review whenever."
with open(path, "w") as f:
    f.write(json.dumps(entry) + "\n")
for problem in ledger.verify():
    print(f"   Caught: {problem}")

shutil.rmtree(folder)
