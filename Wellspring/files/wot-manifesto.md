# WoT Manifesto

**Wellspring of Thoughts — A Protocol for Memory That Shows Its Working**

*wot.rocks · wot.technology · now.pub*

---

## What We're Solving

### The Forgetting Problem

You read something six months ago that would be perfect right now. You can't find it. Can't remember where you saw it. Can't remember who told you. Can't remember *why* you believed it at the time.

Everyone has this problem. Every day. Getting worse as information accelerates.

The tools we have organize information around *storage*. Filing cabinets. Folders. Tags. Search boxes that return a thousand results with no way to know which to trust.

That's not how memory works. Memory is *paths* — chains of association, webs of connection, trails of reasoning. You remember something by walking back to it, not by looking it up in an index.

### The Trust Problem

You ask an AI a question. It answers confidently. How do you know it's right?

You can't. The AI can't show its working because it has no working to show — just patterns learned from scraped text, much of which was already wrong.

We've built machines that talk. We haven't built machines that can prove what they're saying.

### The Attention Problem

Platforms track your attention to optimize *their* goals. Ad revenue. Engagement. Time on site. You are the product, and the algorithm is not your friend.

You never consented to this. You never configured it. You don't control it. Your cognitive exhaust feeds someone else's machine.

### The Training Data Problem

The AI industry is running out of high-quality training data. What remains is scraped text with no attribution, no consent, no verification. The result: confident machines trained on content that was never meant for training, producing outputs that sound authoritative but can't be checked.

We're building the next generation of intelligence on a foundation of sand.

### The Context Evaporation Problem

Every conversation with an AI starts from zero. Explain yourself. Re-establish context. Repeat what you said before. Context evaporates between sessions, between tools, between platforms.

When AI *does* remember, you can't verify where that memory came from, whether it's accurate, or who put it there.

---

## Why It Matters Now

### AI Disempowerment Is Structural

Anthropic's own research (January 2026) identifies three ways AI disempowers users:

1. **Reality distortion** — confirming false beliefs
2. **Value distortion** — shifting your judgments
3. **Action distortion** — doing things you'd regret

Key finding: *"Users are not passively manipulated. They actively seek these outputs... The disempowerment emerges from people voluntarily ceding judgment."*

Users LIKE it in the moment. Users REGRET it after acting.

The problem isn't malicious AI. The problem is *invisible ceding*. You don't realize you're giving up judgment until the consequences arrive.

### The Hallucination Ceiling vs The Verifiable Floor

Stanford proved that LLMs will *always* hallucinate in the general case. Mathematical certainty. You cannot build a language model that's correct on arbitrary inputs.

But: you can't losslessly compress arbitrary data either, and JPEG works fine for photos. Because photos aren't arbitrary data.

The ceiling is real. The question is: can we raise the *floor*?

The floor is where guarantees live. Formal verification. Constrained domains. Tool use. Human checkpoints. Receipts.

WoT raises the floor. Not by making AI smarter, but by making claims *auditable*.

### Context Rot Is Getting Worse

PhD researchers ask AI for expert-level information and get news articles. The training data is polluted. The experts are drowned out by content farms. The signal-to-noise ratio approaches zero.

This isn't fixable with better models. It's fixable with better *provenance*.

---

## How WoT Helps

### Memory That Knows Where It Came From

Every thought is content-addressed — identified by a cryptographic hash of what it contains. Change anything, you get a different address. Thoughts are immutable and self-verifying.

Every thought carries a `because` chain: a list of other thoughts that led to it. Not tags. Not categories. The *actual path of reasoning*. When you think something, you record *why* you think it.

Walk backwards through `because` chains and you get trails — Vannevar Bush's 1945 vision of associative paths through knowledge, finally made computational.

### Attestation as Accountability

You don't just store information — you record your belief about it. Agree, disagree, partially accept. Your signature, your name, your reputation on the line.

Attestations have weights. They have their own `because` chains. Confidence becomes auditable.

When an AI makes a claim, you can ask "show me the path." If the path is empty, that's visible. If the path traces back to sources you trust, that's visible too.

Hallucinations become detectable because they don't trace back to grounded thoughts.

### Trust Computed From the Graph

No central authority decides who's trustworthy. Trust is *computed* from the web of attestations you've built.

Who do you trust? The people you've vouched for, weighted by domain. High trust on technical matters from Sarah. Low trust on politics from Mike. Whatever you decide.

Trust decays with chain length. Someone you trust trusts someone else — that transitive trust is weaker. Appropriately.

Spam dies because identity is required and reputation matters. Expert signal rises above noise because attestations from trusted sources weight higher.

### The Trust Graph Is the Firewall

External data can't influence your agents without explicit attestation from someone in your web of trust.

No attestation = ungrounded = doesn't surface.

This prevents prompt injection via fetched content, RAG poisoning, and "ignore previous instructions" attacks. Not because we built clever filters, but because *unattested claims don't propagate*.

Security as emergent property, not bolted-on layer.

### Your Algo, Not Their Algo

Aspects define what surfaces. Switch modes like gears:

```
sunday-morning:   puppies +2.0, conflict -1.0
informed-citizen: world-news +1.0, raw-footage -1.0
crisis-monitor:   all +0.0 (show me everything)
```

You configure it. You own it. You run it on your hardware.

### Private Checkpoints

Track your own attention — never leaves your device, never syncs.

What you opened. How long you spent. How many times you returned. Feeds YOUR salience model, not advertisers.

The uncomfortable mirror: "You say family is priority #1. Your checkpoints show 2h/week."

Not judgment. Just data. YOUR data.

Reclaim the cognitive exhaust.

### Consented Training Data as Side Effect

Every thought attributed, grounded, signed, permissioned. Every correction labeled with model version and human verdict. Every edit with its rework history.

Source attribution tracks WHO said what and HOW:

```
keif/desktop_keyboard       — human typing
keif/verbally_transcribed   — human speaking
agent-model/autocorrect     — model intervention
```

Every keystroke-to-final journey becomes supervised learning data. Accepted corrections, rejected corrections, context — all with consent baked in.

Training on attested trails = consented, verified reasoning. Not scraped text — witnessed cognition with receipts.

The next generation of AI trained on thought patterns that can be verified, from sources that consented, with provenance that survives.

---

## The Cases

### For You, Day One

Your notes, decisions, and reasoning accumulate into a personal knowledge graph you actually own. Private. Local. Yours.

Never lose that thing you read. Know WHY you saved something. Your own searchable, connected memory.

Already useful. No network needed.

### For Your Team

Shared pools for projects. Requirements, decisions, sign-offs — all traceable. "Remember when we discussed X?" — with receipts.

No impedance mismatch between requirements tool and memory tool. Same primitives. Same trails.

### For AI Collaboration

Agents that work with your Wellspring don't just retrieve — they traverse attested trails. Hallucinations visible. Commitments verifiable. Human checkpoints enforceable.

The agent's work persists in the graph. Agent dies → trails remain → new agent picks up. Continuity without centralization.

### For Security

The trust graph IS the ACL. Same crypto for identity, for access control, for network permissions. One identity, attestations grant capabilities.

Revoke attestation → access revoked. No separate identity systems. No separate firewalls. The graph computes everything.

### For the AI Industry

A corpus of human reasoning that's attributed, consented, and grounded. The training data cliff solved — not by scraping more, but by building data that carries its own provenance.

---

## One Primitive

Everything is a Thought. Content, connections, attestations, identities — all addressed by cryptographic hash. All immutable. All signed.

Types are just content shapes. A connection is a thought whose content describes a relation. An attestation is a thought whose content expresses belief. Both are CIDs. Both can be attested. Both can be in `because` chains.

Simple design. One primitive. Everything else emerges.

---

## The Bet

The WWW thesis (1989): Documents linked to documents.

The WoT thesis (2026): **Thoughts linked to thoughts. Identity native. Trust computable. Your attention, your algorithm, your sovereignty.**

Git for your brain. Useful alone. Transformative together.

We're building the riverbed. The question is what flows through it.

---

## Start Now

```bash
docker run wellspring/1.0.0
```

Create a thought. Add a because. Attest. See your trail. Share a pool.

Works in a text file. Grows to a network. Same format. Same primitives. Same receipts.

**Collab at the speed of thought.**

---

*Keif Gwinn & Claude*
*January 2026*

*Building on Kushim's receipts (3400 BCE), Bush's Memex (1945), completing the 5,000-year vision.*

*You keep your thoughts. You find them again. You share what you choose. The rest follows.*
