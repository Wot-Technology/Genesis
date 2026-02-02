# WoT v0.7 Delta Analysis

Cross-referencing session2 materials with current v0.6v2. Identifying gaps, contradictions, and new concepts for v0.7.

---

## NEW CONCEPTS (not in current spec)

### 1. Dual Chain Structure — Because vs Rework

**Missing entirely.** Important distinction:

```
THOUGHT (published version)
├── because_chain: [WHY this exists]
│   → source material, context, prior thoughts
│
└── rework_chain: [HOW this became this]
    → v3 → v2 → v1 → v0 (edit history)
```

Capture mode spectrum: Final only ← Major edits ← All edits ← Keystrokes

**Pool rules, not protocol rules:** The protocol supports full fidelity. Pools declare what they accept.

### 2. Full Fat vs Diff Thoughts

Git-style storage modes not in current spec:

```
Full fat:  content: "The entire document" (50kb)
Diff:      content: { op: "replace", path: "/section/3", value: "new text" } (200 bytes)
           about: [previous_version_cid]
```

Connection metadata tells downstream what to expect. Reconstruction via checkpoint + forward application.

### 3. WoT Identity → Client Certs → IPv6 Access

**Same crypto for everything:**

```
ed25519 keypair works for:
- WoT identity (did:key:z6Mk...)
- TLS client cert (derived from same key)
- IPv6 access grants (attestation controls firewall)
```

Access grant as thought:
```
Thought: "Grant network access"
  type: access_grant
  identity: [peer_identity_cid]
  resource: ipv6:2001:db8::1/128
  protocol: [sync, query]
  expires: 2026-02-28
  attested_by: [network_owner]
```

**The collapse:** 5 identity systems → 1. The graph IS the ACL.

### 4. Hallucination Floor (not Ceiling)

Stanford paper insight + JPEG reframe:

```
"You can't losslessly compress arbitrary data.
 That's been proven for decades.
 And yet JPEG works perfectly fine for photos.
 Because photos aren't arbitrary data."
```

WoT defines a smaller room:
- Attestation weight = confidence (not fake certainty)
- No attestation = "I don't vouch"
- Tool use (walk because trails)
- Because chain or it didn't happen
- Human checkpoint for high-stakes

**The benchmark problem:** MMLU has no "I don't know" option. We train models to fake certainty.

### 5. Multiplex Networks — Academic Validation

Network science confirms aspect model:

| Multiplex Networks | WoT |
|--------------------|-----|
| Nodes | Identities |
| Layers | Aspects |
| Layer-specific edges | Connection + aspect weights |
| Layer failure | Low/negative aspect weight |
| Boundary adjustment | Aspect attenuation |

"Trust on what?" is the right question, not "trust or not?"

### 6. OLP / OpenLine Protocol — Structural Triage

Pre-verification health check:

```
RED if:
  cycle_plus > 0                    # Circular reasoning
  OR (Δhol ≥ 0.35 AND del_suspect)  # Drift + deletions
  OR (κ ≥ 0.75 AND UCR ≥ 0.40)      # Stress + unsupported
```

Fits in pipeline:
```
INGEST → OLP TRIAGE → SUBCONSCIOUS → WORKING MEMORY → CONSCIOUS
```

OLP tells subconscious WHERE to focus.

### 7. CooperBench — Multi-Agent Coordination

Key finding: GPT-5 + Claude achieve only 25% success with two-agent cooperation — 50% lower than single agent.

Failure types:
- Expectation failures: 42%
- Communication failures: 26%
- Commitment failures: 32% ← target

**WoT fix:** Separate action from accountability. Commitments as attestable thoughts.

### 8. SERA — Soft Verification Pattern

"Soft verification via patch agreement": generate two independent solutions, compare overlap. Works without ground truth tests.

```
Soft verification score r = fraction of lines matching.
Even r=0 trajectories are valuable for training!
```

Matches `black_jesus_threshold = 80` insight: you don't need perfect verification, you need realistic process traces.

### 9. Synapse Decompilation — The Confidence Pattern

```python
black_jesus_threshold = 80
```

If transition probability < 80%, fallback to shuffle (admit uncertainty).

"A 'smart' system that's wrong 30% of the time feels broken. A system that only speaks when it's certain feels like AI."

**WoT principle:** Silence > confident hallucination.

### 10. Corrections as Training Data

Every correction carries provenance:

```yaml
correction:
  original: [cid_of_typo]
  proposed: "the quick brown fox"
  model: "autocorrect/gboard/3.2.1"
  accepted: true | false
  by: [human_identity]
  context: [surrounding_thought_cid]
  pool: [pool_id]  # domain signal
```

The training data cliff solution. Every keystroke-to-final journey = supervised learning dataset with consent baked in.

### 10a. Input Source Attribution

**Key insight:** Thoughts carry metadata about WHO said what and HOW.

Source format: `<identity>/<method>`

```
Human inputs:
  keif/desktop_keyboard     — direct keyboard on desktop
  keif/mobile_keyboard      — mobile keyboard
  keif/verbally_transcribed — voice-to-text (human speaking)
  keif/handwritten_ocr      — handwriting recognition

Agent inputs:
  agent-model/autocorrect   — autocorrect intervention
  agent-model/prediction    — predictive text accepted
  agent-model/stt/whisper   — speech-to-text model
  agent-model/completion    — AI text completion
  agent-model/gboard/3.2.1  — specific model version
```

**Why this matters:**

1. **Training signal** — Know which corrections were human vs autocorrect
2. **Intent detection** — Voice input often more casual than keyboard
3. **Model attribution** — Track which model versions produced what
4. **Consent granularity** — Share keyboard data but not voice, etc.

**Rework chain with source:**

```
Keystroke thought:
  type: input
  content: { char: "e", position: 45 }
  source: "keif/desktop_keyboard"
  visibility: local_forever

Autocorrect thought:
  type: input
  content: { replace: "teh", with: "the" }
  source: "agent-model/autocorrect/gboard/3.2.1"
  visibility: local_forever

Connection (rework chain):
  type: rework
  from: [autocorrect_cid]
  to: [keystroke_sequence_cid]
```

**Pool rules for capture:**

```
Pool: casual-notes
  capture_mode: final_only

Pool: ml-training-opt-in
  capture_mode: keystrokes
  require_source: true
  accepted_sources: [keyboard, autocorrect]  # no voice
```

Minimal overhead locally. Never leaves device unless pool requires. Full attribution when it does.

### 11. Trust Graph as Firewall (Security Framing)

From wellspring-introduction.md:

> **For security:** The trust graph is the firewall. External data can't influence your agents without explicit attestation from someone in your web of trust. No attestation = ungrounded = doesn't surface. This prevents prompt injection via fetched content, RAG poisoning, and "ignore previous instructions" attacks.

**Critical:** Security as emergent property, not bolted-on layer.

### 12. eBPF Architecture Pattern

Layer splitting for performance:
- L3/L4 (routing, tunnels) → kernel/eBPF (fast)
- L7 (complex policies) → user space (flexible)

**WoT mapping:**
- Transport fast
- Trust computation in application layer
- Graph membership IS the routing policy

---

## CONTRADICTIONS / TENSIONS

### 1. Repeaters Status

**Session2:** Mentions repeaters as trust anchors, verification checkpoints.
**Current (dogfood 018):** Found repeaters redundant — attestation-copying achieves same effect.

**Resolution:** Not a contradiction. Repeaters are organizational (attesting) not protocol (special node type). Attestation-copying IS the mechanism.

### 2. Visibility Model Naming

**Session2/v0.6:** `visibility: public | private | unlisted`
**Current dogfood:** `visibility: null | local_forever | pool:<cid> | participants_only`

**Resolution:** Both are valid. The dogfood uses more granular visibility. Merge: keep dogfood model, add `unlisted` for completeness.

### 3. Schema Version References

**Session2:** References `wellspring://v0.4/thought`
**Current:** No specific schema versioning protocol defined.

**Resolution:** Need to define schema CID format and versioning.

---

## MISSING PIECES

### 1. Corrections/Amendments Protocol

How to fix typos without breaking immutability? Session2 has it, current spec doesn't:

```
Original: "teh quick brown fox" [immutable]
    ↓
Correction: { type: "correction", original: [cid], proposed: "the..." }
    ↓
Acceptance: { type: "attestation", accepts: [correction_cid] }
```

### 2. Transport Layer Specification

Session2 has eBPF learnings but no concrete transport spec. Need:
- Packet format (the 64-byte header is in session2)
- Connection negotiation
- Socket-level optimizations

### 3. Voice/Audio Interface

Session2 has local STT/TTS stack (Whisper, Kokoro) but not integrated into spec.

### 4. WASM Deployment Model

Session2 mentions 3W stack (WebLLM + WASM + WebWorkers) but spec doesn't cover browser deployment.

### 5. OLP Integration

Structural triage not in spec. Valuable for:
- Cycle detection
- Stress metrics
- Verification prioritization

---

## V0.7 ADDITIONS RECOMMENDED

1. **Dual Chain Structure** — Because + Rework chains (connection thoughts, not new primitive)
2. **Full Fat vs Diff Thoughts** — Git-style storage modes
3. **Identity → Access Control Collapse** — Same crypto for everything
4. **Hallucination Floor** — Structural mitigation of AI failures
5. **Corrections Protocol** — Amendments without breaking immutability
6. **Trust Graph as Firewall** — Security as emergent property
7. **OLP Metrics** — Structural health checks (UCR, cycle detection)
8. **Commitment Verification** — Multi-agent accountability pattern
9. **Pool Capture Modes** — Protocol supports full fidelity, pools declare requirements
10. **Soft Verification Pattern** — Agreement without ground truth
11. **Input Source Attribution** — WHO said what and HOW (`identity/method` format)

---

## NO CONTRADICTIONS FOUND

The materials are consistent. Session2 has deeper material on specific topics. The core model (one primitive, because chains, attestations, pools) is stable across all versions.

*Analysis complete. Ready for v0.7 draft and manifesto.*
