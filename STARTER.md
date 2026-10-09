# Build your own Jarvis-style layer on Grok

One afternoon. Free. No code needed until step 6, and that step is optional.

The idea: Grok stays the engine. You put your own layer on top with your own name, your own rules and your own final veto. Grok suggests. You decide. You keep the record.

**You need:** a Grok account (the free tier is fine, on grok.com or in the X app) and a notes app. For step 6, Python 3.9 or newer.

---

## 1. Name it (10 minutes)

Pick a name for your layer. Write this at the top of your notes and keep it:

```text
My layer is called [NAME] (@grok).
[NAME] is mine: my rules, my veto, my record.
Grok is the engine underneath. I don't own Grok and I'm not changing it.
```

The brackets matter. "[NAME]" is yours. "(@grok)" marks the engine.

## 2. Write 5 to 10 rules (30 minutes)

Short, plain, and things you can check. Start from these and change them to fit you:

```text
1. You propose. I decide. Nothing is saved, posted or acted on without my "yes".
2. My "no" is final. Don't bring a vetoed idea back unless I ask.
3. Say what is real today and what is still an idea. Never call something
   "online" or "live" unless I can check it myself.
4. Name your own overclaims before I have to.
5. Plain words. Short answers unless I ask for more.
6. What matters most to me comes first: [FILL IN].
7. When you are guessing, say so.
8. [Your own rule]
9. [Your own rule]
10. [Your own rule]
```

## 3. The morning anchor (5 minutes a day)

A chat model doesn't reliably remember you from one chat to the next. Continuity comes from you re-anchoring it each day. Start each day with one message:

```text
Good morning [NAME] (@grok).
Re-anchor: [paste your rules].
Yesterday I approved: [one or two lines from your record].
Today's one proposal or question: [one thing].
Propose only. I'll approve or veto.
```

## 4. The habit: propose, then veto

Ask for proposals, not decisions:

```text
Propose, don't decide. Give me 3 options for [THING], one line each,
and mark which parts are guesses.
```

Then answer in one line: `Approve 2.` or `Veto 1 and 3.`

The rule of thumb: **if you didn't say yes, it didn't happen.**

End-of-day check, two questions: Did what matters most stay first today? Did I keep the last word?

## 5. Keep a record (private or public)

**Private:** one dated line per decision in a notes file:

```text
2026-10-08 | proposed: [what] | decision: approve / veto | why: [one line]
```

**Public (optional):** one short post a day, for example:

```text
Today's veto call: [old line] -> [new line]. My call: [keep / clear].
```

A public record is harder to quietly rewrite, and it shows your work over time. Keep personal details out of it.

## 6. Run the Intent Ledger (optional, 10 minutes)

The [Intent Ledger](intent-ledger/) does steps 4 and 5 for you on your own computer. Proposals wait in a queue, nothing is saved without your approve, a veto is final, and any later edit to the record is caught.

First check you have Python 3.9 or newer (`python3 --version`), then get a copy of this repo, either with git or by using the green Code button on GitHub and choosing Download ZIP.

```bash
git clone https://github.com/k5xh997hv8-art/Jarvis-Grok.git
cd Jarvis-Grok/intent-ledger
python3 example.py
python3 intent_ledger.py propose "Weekly review every Sunday at 18:00."
python3 intent_ledger.py pending
python3 intent_ledger.py approve <id>      # or: veto <id>
python3 intent_ledger.py verify
```

---

## Optional: four handles to remember the habit

Some people find names easier to remember than a list of rules. These are labels for jobs, nothing more. They are tools, not claims about anything mystical.

| Handle | The job | Where it shows up |
| --- | --- | --- |
| **Flame** | What matters most comes first. | Rule 6 |
| **Guardian** | Nothing is kept without your yes. | Rules 1 and 2, the ledger's Guardian tests |
| **Architect** | Keep things in order and on the record. | Step 5, the ledger's Architect tests |
| **Shadow** | Name the overclaim before anyone else does. | Rules 3 and 4, the ledger's Shadow tests |

## What not to claim

- You have not changed Grok. Your layer is your rules and your record on top of it.
- It is not an official xAI product, and it is not "online" or "live" in any technical sense unless you built and can check something that is.
- Check xAI's own terms before you sell or license anything you make with Grok.

---

Built by Tommy Maloney with Grok. Independent, not affiliated with or endorsed by xAI / SpaceX AI.
