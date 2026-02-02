# Thread 1 → Commercial/Licensing Thread Handoff

**From:** Thread 1 (RFC/Protocol)
**To:** Commercial & Licensing Thread
**Date:** 2026-01-31

---

## Context

Thread 1 established the WoT protocol specification. This handoff covers commercial strategy, licensing decisions, and business model refinement.

---

## Current Licensing Position

### Protocol & Spec
- **Recommendation:** CC-BY-4.0 (open, attribution required)
- **Rationale:** Protocol must be open for network effect. Like TCP/IP.

### Reference Implementation
- **Recommendation:** AGPL-3.0 (copyleft)
- **Rationale:** Forces contribution from anyone offering WoT-as-a-service. Protection against AWS-style extraction.
- **Alternative:** Dual MIT/Apache-2.0 + Commercial license (requires CLA)

### Service Layer (now.pub)
- **Structure:** Commercial LLC, separate from protocol
- **Relationship:** Protocol can't be captured by now.pub; now.pub operates independently

---

## Dependencies (All Permissive)

| Dependency | License | Notes |
|------------|---------|-------|
| Protocol Buffers | BSD-3 + Apache-2.0 | Patent grant via Apache |
| BLAKE3 | CC0 OR Apache-2.0 | Dual license, user chooses |
| gRPC | Apache-2.0 | Some BSD-3 components |
| libp2p | MIT/Apache-2.0 | Dual license |
| Ed25519 libs | BSD-3/MIT/Apache | Varies by implementation |

No copyleft dependencies. All compatible with AGPL, MIT, Apache, and proprietary.

See: `thread-1/LICENSING.md` for full breakdown.

---

## now.pub Business Model

### Service Tiers

| Tier | Price | What You Get |
|------|-------|--------------|
| **Free** | $0 | Identity claim, DNSSEC, bootstrap peering |
| **Pro** | $5-15/mo | CDN peering, DDoS protection, IP hidden |
| **Storage** | $0.05-0.10/GB/mo | IPFS pinning, thought persistence |
| **Enterprise** | $500+/mo | Dedicated infra, SLA, compliance |

### Key Value Props

1. **CDN Peering:** "Don't expose your home IP. We take the heat, verify signatures at edge, forward clean traffic."

2. **Storage:** "Your thoughts survive your laptop closing."

3. **Discovery:** now.pub is THE bootstrap. Network effect compounds.

See: `thread-1/now-pub-business-model.md` for full model.

---

## NEW: Expertise-as-Context Business Model

**Insight from parallel discussion:**

> "The commercial angle: expertise-as-context, sold as files that make AI useful in your domain. Essentially selling 'pre-warmed state' rather than raw capability."

### The Concept

WoT thought pools aren't just data — they're **curated, attested knowledge graphs** with provenance. This is valuable:

```
RAW AI CAPABILITY          EXPERTISE-AS-CONTEXT
──────────────────         ─────────────────────
Generic model              + Domain thought pool
No context                 = Useful specialist
Hallucinates               = Grounded in because chains
No provenance              = Auditable sources
```

### What You're Selling

**Not data. Not training. Pre-warmed state.**

| Product | Description | Example |
|---------|-------------|---------|
| **Domain Pools** | Curated thought chains for specific industries | "Legal precedent pool", "Medical guidelines pool" |
| **Expert Trails** | Attested reasoning paths from domain experts | "How Dr. X diagnoses condition Y" |
| **Compliance Packs** | Pre-verified thought chains for regulatory contexts | "GDPR compliance reasoning", "SOC2 audit trails" |
| **Onboarding Packs** | Company-specific context for new AI deployments | "How we do things at Acme Corp" |

### How It Works

```
EXPERT CREATES THOUGHTS
        │
        ├── Curated, because-chained
        ├── Attested by expert identity
        └── Published to purchasable pool
                │
                ▼
BUYER SUBSCRIBES TO POOL
        │
        ├── Syncs thoughts to local daemon
        ├── AI retrieves via RAG (Thread 2)
        ├── Responses grounded in expert trails
        └── Attribution preserved (because chains)
```

### Pricing Models

| Model | Description | Example |
|-------|-------------|---------|
| **Subscription** | Monthly access to updating pool | $50-500/mo for legal updates |
| **One-time** | Static snapshot pool | $500 for "startup legal basics" |
| **Per-seat** | Enterprise license per user | $20/user/mo |
| **Revenue share** | % of downstream value created | Complex, needs tracking |

### Why WoT Enables This

1. **Provenance:** Every thought has `created_by` and `because` chain. Know who said what and why.

2. **Attestation:** Experts attest quality. Buyers trust based on attestor reputation.

3. **Incremental updates:** Subscribe to pool, get updates as expert adds thoughts.

4. **Access control:** `chain_access` gates who can read what. Paid pools are private.

5. **No lock-in:** Thoughts are portable. Cancel subscription, keep what you synced.

### Integration with now.pub

```
now.pub MARKETPLACE (future)
─────────────────────────────
├── Browse domain pools
├── Preview (intro thoughts public)
├── Subscribe (now.pub handles payment)
├── Sync (CDN delivers thoughts)
└── Revoke on non-payment (chain_access expires)
```

now.pub becomes not just identity/CDN but also **marketplace for expertise**.

---

## Domain Acquisition Strategy

### Currently Own
- now.pub (identity, bootstrap, CDN)

### Recommended Acquisitions

| Domain | Price | Use Case |
|--------|-------|----------|
| wot.chat | £36.99/yr | Social discovery, pool chat |
| wot.team | £36.99/yr | Collaboration, org pools |
| wot.support | £7.99/yr | Docs, help, support |
| wot.link | £369.99/yr | Premium — literally "linking thoughts" |

### Maybe Later

| Domain | Price | When |
|--------|-------|------|
| wot.media | £36.99 | If content publishing takes off |
| wot.company | £19.99 | Enterprise branding |
| wot.capital | £11.99 | If funding/token angle emerges |

---

## Open Questions for This Thread

### Licensing
1. AGPL vs Dual License for reference impl — which protects better?
2. CLA (Contributor License Agreement) — needed if dual licensing?
3. Trademark registration for "WoT", "Web of Thought", "now.pub"?

### Commercial
4. Expertise marketplace — who curates? Quality control?
5. Pricing strategy — subscription vs one-time for domain pools?
6. Enterprise sales — direct or channel partners?
7. VC funding vs bootstrap — tradeoffs for protocol adoption?

### Legal Structure
8. Jurisdiction for now.pub LLC — US, UK, EU?
9. Separate foundation for protocol governance — when/if?
10. IP assignment — who owns what contributions?

---

## Key Files to Read

- `thread-1/LICENSING.md` — Dependency licenses, compatibility matrix
- `thread-1/now-pub-business-model.md` — Tiered service model
- `thread-1/schemas-core.md` — How chain_access enables paid pools
- `thread-1/traces.jsonl` — 54 decision traces (search for "license", "business")

---

## The Big Picture

```
PROTOCOL (open)              SERVICES (commercial)
───────────────              ────────────────────
CC-BY-4.0 spec               now.pub LLC
AGPL-3.0 impl                │
                             ├── Identity/Bootstrap (free)
Anyone can implement         ├── CDN Peering (paid)
Anyone can self-host         ├── Storage (paid)
Network effect grows         ├── Enterprise (paid)
                             └── Expertise Marketplace (paid)
                                    │
                                    └── Sellers: Domain experts
                                        Buyers: AI deployers
                                        Cut: now.pub takes %
```

**Your position:**
- Protocol creator (authority)
- Reference impl maintainer (influence)
- now.pub operator (revenue)
- Marketplace platform (network effects)

**Protection:**
- AGPL forces contribution from service providers
- First-mover trust advantage
- Expertise marketplace has natural moat (curation, quality)

---

## Next Steps for Commercial Thread

1. [ ] Finalize license choice (AGPL vs dual)
2. [ ] Draft CLA if dual licensing
3. [ ] Incorporate now.pub entity
4. [ ] Trademark search/registration
5. [ ] Develop expertise marketplace concept
6. [ ] Pricing research for domain pools
7. [ ] Create pitch deck (if raising)
8. [ ] Legal review of full structure
