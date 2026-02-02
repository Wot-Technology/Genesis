# Wellspring: Memory That Knows Where It Came From

## The Problem

Every conversation with an AI starts from zero. Context evaporates. You explain the same things repeatedly. When the AI does "remember," you can't verify where that memory came from or whether it's real.

Meanwhile, the AI industry is running out of training data. What remains is scraped text with no attribution, no consent, and no way to check if any of it is true. The result: confident machines that hallucinate, trained on content that was never meant to be training data.

We've built AI that can talk. We haven't built AI that can *show its working*.

## The Idea

Wellspring is a protocol for building memory that carries its own provenance.

Every thought is content-addressed — identified by a cryptographic hash of what it contains. Change anything, you get a different address. This makes thoughts immutable and self-verifying.

Every thought carries a `because` field: a list of other thoughts that led to it. Not tags. Not categories. The actual chain of reasoning. When you think something, you record *why* you think it.

Every thought can be attested. You don't just store information — you record your belief about it. Agree, disagree, partially accept. Attestations have weights and their own `because` chains. Confidence becomes auditable.

Walk backwards through `because` chains and you get trails — Vannevar Bush's 1945 vision of associative paths through knowledge, finally made computational.

## What This Enables

**For individuals:** Your notes, decisions, and reasoning accumulate into a personal knowledge graph you actually own. Not locked in an app. Not scraped by platforms. Yours.

**For collaboration:** Share pools of thoughts with others. Trust is computed from the graph itself — who vouched for whom, which attestations hold up, where reasoning diverges. Disagreement becomes visible and productive.

**For AI:** Agents that work with your Wellspring don't just retrieve information — they traverse attested trails. When they make claims, you can ask "show me the path." Hallucinations become detectable because they don't trace back to grounded thoughts.

**For security:** The trust graph is the firewall. External data can't influence your agents without explicit attestation from someone in your web of trust. No attestation = ungrounded = doesn't surface. This prevents prompt injection via fetched content, RAG poisoning, and "ignore previous instructions" attacks. Every piece of external information that affects your system has an auditable trail showing who vouched for it and why.

**For training:** A corpus of human reasoning that's attributed, consented, and grounded. Not scraped text — witnessed cognition with receipts. The next generation of AI trained on thought patterns that can be verified.

## How It's Different

| Current Tools | Wellspring |
|---------------|------------|
| Memory is opaque | Memory shows its sources |
| AI confidence is performed | Confidence is computed from attestation depth |
| Data is extracted | Data is contributed with consent |
| Context resets per session | Context persists and accumulates |
| Trust is assumed | Trust is earned through the graph |
| Collaboration means sharing files | Collaboration means sharing reasoning |

## The Technical Foundation

- **One primitive:** Everything is a Thought — content, connections, attestations, identities, all addressed by cryptographic hash
- **Storage:** IPFS for content-addressed distribution, IPNS for stable naming
- **Local-first:** Your data lives on your devices, syncs on your terms
- **Interoperable:** Any tool can read/write thoughts via the protocol

## Where This Goes

Wellspring isn't an app. It's infrastructure for a different kind of memory — one where provenance is built in, not bolted on.

The AI systems of the next decade will be trained on something. It can be more scraped internet with no accountability. Or it can be human knowledge that knows where it came from, who believed it, and why.

We're building the riverbed. The question is what flows through it.

---

*Wellspring is currently in design. This document describes intent, not shipping software.*
