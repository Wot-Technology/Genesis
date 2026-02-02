# WoT Sites Checkpoint — 2026-01-31

**Status:** Landing pages built, Cloudflare env in prep, demos identified

---

## What's Live (or ready to deploy)

### Static Sites
- `wot.rocks` — Consumer pitch, waitlist form
- `wot.technology` — Protocol overview, SDK access form
- `now.pub` — Identity reservation, subdomain claim form

### Form Worker
- Rust Cloudflare Worker scaffolded
- KV-backed storage for signups
- Endpoints for all three sites
- Pending: KV namespace creation, deployment

---

## Tech Demos Identified

### 1. now.pub Status Alignment
**What:** User's local agent pushes signed status updates to now.pub peering node → DNS TXT records update

**Why it's good:**
- Simplest useful WoT interaction
- Zero complexity visible to user
- Full protocol underneath (signed thoughts, peering, sync)
- Derek Sivers /now evolution angle
- Bot availability too (queue depth, estimated wait)

**Implementation path:**
- User claims subdomain (form exists)
- User runs local daemon with now.pub peering configured
- Daemon creates status thoughts, signs, pushes
- now.pub verifies sig, updates DNS TXT
- `keif.now.pub TXT "status=building-wot"`

### 2. No (無) — Adversarial Game
**What:** Go variant with void/nuclear mechanic, played over WoT

**Why it's good:**
- Collab without chat
- Signed moves, mutual attestation per turn
- Because chains = game history
- "Your name is on the button, forever, in the chain"
- Demonstrates: shared state, accountability, dispute auditability

**Files:** `wot-no/` — go-san.html, no.html, rules, handover doc

**Implementation path:**
- Define thought schemas for moves/attestations
- Add ed25519 signing to existing HTML clients
- Pool creation for game sessions
- Real-time sync via peering
- Spectator mode (read-only pool access)

---

## Commercial Model (Not for landing pages yet)

### now.pub Tiers

| Tier | Price | Value Prop |
|------|-------|------------|
| **Free** | $0 | Identity claim, DNSSEC, rate-limited peering |
| **Pro** | $5-15/mo | CDN peering, DDoS protection, IP hidden |
| **Key Custody** | $3-5/mo | Encrypted backup, recovery, estate planning |
| **Storage** | $0.05-0.10/GB | IPFS pinning, thoughts persist offline |
| **Enterprise** | $500+/mo | Dedicated infra, SLA, compliance |

### Key Custody Details
- Encrypted key backup (now.pub never sees unencrypted)
- Recovery via video call + govt ID + security questions
- 24-hour challenge period (can cancel from any remaining device)
- SAME_AS signing to new key on behalf
- Estate planning: designated heirs, death certificate flow
- **Pitch:** "Your identity survives your laptop, your house fire, and you."

### Expertise-as-Context
- Curated thought pools as "pre-warmed AI state"
- Domain experts attest, buyers subscribe
- AI grounds responses in because chains
- now.pub as marketplace (future)

**Products:**
- Domain Pools (legal precedent, medical guidelines)
- Expert Trails (attested reasoning paths)
- Compliance Packs (GDPR, SOC2 audit trails)
- Onboarding Packs (company-specific context)

### Revenue Projections (Conservative Y1)
- Free: 10,000 users
- Pro: 500 @ $10 = $5,000 MRR
- Key Custody: 300 @ $4 = $1,200 MRR
- Storage: 200 @ $5 = $1,000 MRR
- Enterprise: 5 @ $1,000 = $5,000 MRR
- **Total:** ~$12-17k MRR = $145-200k ARR

---

## Licensing Position

| Component | License | Rationale |
|-----------|---------|-----------|
| Protocol Spec | CC-BY-4.0 | Open for network effect |
| Reference Impl | AGPL-3.0 | Forces contribution from service providers |
| now.pub Service | Commercial | Separate entity, revenue vehicle |

All dependencies (protobuf, BLAKE3, gRPC, libp2p, ed25519) are permissive. No copyleft contamination.

---

## Domain Strategy

### Own
- wot.rocks, wot.technology, now.pub

### Recommended
- wot.chat (£36.99/yr) — social discovery
- wot.team (£36.99/yr) — org collab
- wot.support (£7.99/yr) — docs/help
- wot.link (£369.99/yr) — premium, "linking thoughts"

---

## Next Actions

### Immediate
- [ ] Create Cloudflare KV namespace
- [ ] Deploy form worker
- [ ] Deploy static sites to Pages
- [ ] Wire custom domains

### Demo 1: Status Alignment
- [ ] Minimal daemon that creates status thoughts
- [ ] now.pub peering endpoint
- [ ] DNS update on verified status push
- [ ] End-to-end: claim subdomain → run daemon → see DNS update

### Demo 2: No Game
- [ ] Move/attestation thought schemas
- [ ] Add signing to HTML clients
- [ ] Two-player sync via pool
- [ ] Replay via because chain traversal

### Later
- [ ] Update landing pages with commercial tiers
- [ ] Incorporate now.pub entity
- [ ] Trademark search (WoT, Web of Thought, now.pub)
- [ ] Expertise marketplace design

---

## Key Files

```
thread-1/
├── now-pub-business-model.md   # Full tier breakdown
├── handoff-commercial-licensing.md  # Licensing + expertise model
├── schemas-core.md             # Thought type definitions
├── wot-wire-format-draft.md    # CID, CBOR, packet format
└── traces.jsonl                # Decision log

wot-no/
├── no.html                     # MAD variant
├── go-san.html                 # Bounded variant
├── go-san-wot-handover.md      # Protocol mapping
└── go-san-rules.md             # Physical play rules

wot-sites/
├── shared/design-system.css    # Brand colors, components
├── wot-rocks/index.html        # Consumer landing
├── wot-technology/index.html   # Technical landing
├── now-pub/index.html          # Identity reservation
└── form-worker/                # Rust CF Worker
```

---

*Checkpoint created: 2026-01-31*
*Resume from here when demos working*
