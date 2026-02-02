# now.pub Business Model

**Status:** Draft
**Updated:** 2026-01-31

---

## Overview

The WoT protocol is open (CC-BY-4.0 spec, AGPL-3.0 reference implementation).

now.pub is the canonical bootstrap service and monetization vehicle.

**Philosophy:** Provide genuine value at each tier. Not artificial lock-in — users can always self-host. But convenience has value.

---

## Service Tiers

### Free: Hello Service

**What you get:**
- One identity claim (`yourname.now.pub`)
- DNSSEC-signed TXT records (WoT CID, IPNS, .onion)
- Basic discovery (resolve name → identity)
- Rate-limited bootstrap peering (connect to network)
- Community support

**Limits:**
- 1 identity per account
- 100 peer connections/day
- No CDN relay
- No storage

**Purpose:** Onboard users, build network effect, establish now.pub as THE bootstrap.

---

### Pro: CDN Peering

**Price:** $5-15/month (TBD based on costs)

**What you get:**
- CDN edge network absorbs inbound traffic
- Signature verification at edge (reject bad actors before they reach you)
- Your home IP never exposed to peers
- DDoS protection
- Geo-distributed relay nodes (lower latency)
- Priority peering (your thoughts relay faster)
- 10 identity claims
- Basic analytics (peer count, thought volume)

**How it works:**
```
INTERNET                    now.pub CDN                YOUR DAEMON
─────────                   ───────────                ───────────

Peers connect to ──────►   Edge node
now.pub relay              │
                           ├─► Verify signatures
                           ├─► Rate limit
                           ├─► Check appetite rules
                           │
                           └─► Forward valid ──────►  Your daemon
                               thoughts only          (home/VPS)
```

**Value prop:** "You run your daemon, we protect it."

---

### Storage: CID Persistence

**Price:** $0.05-0.10/GB/month (competitive with S3/IPFS pinning)

**What you get:**
- IPFS pinning for your thoughts
- Guaranteed availability (your thoughts exist even when you're offline)
- Redundant storage (3+ replicas)
- Bandwidth included for retrieval
- Automatic pinning of new thoughts (daemon integration)
- Storage analytics

**How it works:**
```
Your daemon creates thought
        │
        ├─► Local storage
        │
        └─► Push to now.pub ──►  IPFS pin
                                 │
                                 ├─► Replicated storage
                                 ├─► CDN cache
                                 └─► Always retrievable
```

**Value prop:** "Your thoughts survive your laptop closing."

---

### Key Custody: Identity Insurance

**Price:** $3-5/month (or bundled with Pro)

**What you get:**
- Encrypted key backup stored by now.pub
- Recovery via identity verification (video call, security questions)
- 24-hour challenge period before key release (you can cancel)
- Option: now.pub signs SAME_AS to your new key on your behalf
- Audit log of all custody access attempts
- Estate planning integration (designated heirs)

**How it works:**

```
BACKUP FLOW:
1. You generate keypair locally (we never see unencrypted)
2. You encrypt to now.pub custody pubkey
3. Submit encrypted blob → we store it
4. Your daemon keeps working normally

RECOVERY FLOW:
1. You contact now.pub: "I lost my key"
2. Identity verification (video call, govt ID, security questions)
3. 24-hour hold (you can cancel via any remaining device)
4. If no cancellation → key decrypted and returned
   OR → we sign SAME_AS to your new identity

ESTATE FLOW:
1. You designate heirs in custody settings
2. Death certificate + heir identity verification
3. Key transferred to designated heir
4. Heir creates SAME_AS with inheritance attestation
```

**Value prop:** "Your identity survives your laptop, your house fire, and you."

**Who needs this:**
- Users without technical backup skills
- High-value identities (business accounts, public figures)
- Estate planning conscious users
- "I just want insurance" crowd

**Who doesn't:**
- Technical users with BIP39 backups
- Privacy maximalists (won't trust any third party)
- Multi-device users (device pool is enough)

---

### Enterprise: Dedicated

**Price:** Custom ($500-5000+/month based on scale)

**What you get:**
- Dedicated infrastructure (not shared)
- Custom domain (`identity.yourcompany.com`)
- SLA guarantees (99.9%+ uptime)
- Compliance support (SOC2, GDPR, etc.)
- Audit logs
- Priority support (Slack/email)
- White-label option (your branding)
- Volume discounts on storage

**Target:** Companies running internal WoT pools, regulated industries, large deployments.

**Value prop:** "Your org's WoT, our ops."

---

## Revenue Projections (Rough)

| Tier | Users | Price | MRR |
|------|-------|-------|-----|
| Free | 10,000 | $0 | $0 |
| Pro | 500 | $10 | $5,000 |
| Key Custody | 300 | $4 | $1,200 |
| Storage | 200 @ 10GB avg | $0.50 | $1,000 |
| Enterprise | 5 | $1,000 | $5,000 |

**Conservative Year 1:** $12-17k MRR = $145-200k ARR

Scales with adoption. Protocol success = now.pub success.

---

## Cost Structure

### CDN/Infrastructure
- Edge nodes (Cloudflare Workers, Fly.io, or own): $500-2000/mo to start
- IPFS pinning (Pinata, Filebase, or own): $0.02-0.05/GB
- Compute for verification: scales with traffic

### Operations
- Domain/DNS: minimal
- Monitoring: $50-200/mo
- Support tooling: $100-500/mo

### Margins
- Pro tier: ~70-80% margin (mostly automated)
- Storage tier: ~50-60% margin (commodity costs)
- Enterprise: ~80%+ margin (high touch but high price)

---

## Competitive Moat

### Why now.pub wins:

1. **First mover:** Protocol creators run THE bootstrap
2. **Network effect:** Everyone connects through now.pub initially
3. **Trust anchor:** now.pub attestations have weight ("verified by now.pub")
4. **Convenience:** Self-hosting is possible but now.pub is easier
5. **Expertise:** We wrote the protocol, we know how to run it

### Why users can still leave:

1. **Open protocol:** Nothing proprietary
2. **Data portability:** Export your thoughts, point DNS elsewhere
3. **Self-host option:** Always available
4. **No lock-in:** Competitive pressure keeps us honest

This is the good kind of moat — we win by being best, not by trapping users.

---

## Growth Strategy

### Phase 1: Bootstrap (Months 1-6)
- Free tier only
- Build user base
- Establish now.pub as the default
- Gather feedback

### Phase 2: Monetize (Months 6-12)
- Launch Pro tier
- Launch Storage tier
- Convert power users
- First revenue

### Phase 3: Enterprise (Year 2+)
- Enterprise outreach
- Custom deployments
- Foundation/governance conversations
- Sustainable business

---

## Integration with Protocol Economics

### The virtuous cycle:

```
More users ──► More thoughts ──► More value in network
     ▲                                    │
     │                                    ▼
     └────── now.pub revenue ◄─── Users pay for convenience
```

### Protocol stays open because:

1. Open protocol = more adoption = larger network = more now.pub customers
2. AGPL reference impl = improvements flow back
3. Spec is CC-BY = anyone can implement = ecosystem grows

### now.pub stays viable because:

1. Convenience has value (most won't self-host)
2. CDN/storage are real services (not artificial restrictions)
3. Enterprise needs support (can't just download and run)
4. First-mover trust advantage

---

## Risks

| Risk | Mitigation |
|------|------------|
| Big player forks and competes | AGPL forces open source; we have brand/trust |
| Self-hosting becomes too easy | Offer real value (CDN, storage, support) |
| Protocol doesn't take off | Keep costs low until traction proven |
| Pricing wrong | Start low, iterate based on willingness to pay |

---

## Legal Structure

**Recommendation:**

- **now.pub LLC** (or Ltd depending on jurisdiction)
- Owns: now.pub domain, service infrastructure, trademarks
- Operates: Bootstrap service, CDN, storage
- Employs: You (salary + equity)

**Separate from protocol:**

- Protocol spec: CC-BY-4.0 (open)
- Reference impl: AGPL-3.0 (copyleft)
- Future foundation could steward protocol
- now.pub remains commercial entity

This separation protects both:
- Protocol can't be captured by now.pub
- now.pub can operate commercially without protocol governance interference

---

## Next Steps

1. [ ] Incorporate now.pub entity
2. [ ] Set up basic infrastructure (domain, DNS, monitoring)
3. [ ] Build free tier MVP
4. [ ] Soft launch with early adopters
5. [ ] Gather feedback, iterate
6. [ ] Add paid tiers when demand proven
