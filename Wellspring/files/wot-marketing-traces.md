# WoT: Marketing Traces

**Sources for website content — wot.rocks · wot.technology · now.pub**

These are the "spin-friendly" insights from development. Technical depth lives in `wellspring-traces.md`. This doc captures the human-friendly angles.

---

## One-Liners

**Core pitch:**
- "Your computer buddy. Your external brain. Your web of trust."
- "Collab at the speed of thought."
- "Memory isn't storage — memory is traversal history."

**Trust angle:**
- "You don't get what the internet thinks. You get what people you trust think, with receipts."
- "Same query, completely different results — because your trust graph is yours."
- "Not 'most relevant' — fastest verified trail."

**Privacy angle:**
- "Your thoughts are private until you publish them."
- "Your algorithm, your responsibility."
- "Secrets are just thoughts with visibility rules."

**Provenance angle:**
- "Because chains or it didn't happen."
- "Attestation = skin in the game."
- "5,000-year circle: first writing was receipts for beer. Wellspring is receipts for cognition."

---

## Soundbites by Feature

### Pool-Peer-Rules (Keyvault Collapse)

**Problem:** You have separate systems for secrets, data, permissions, audit logs. They don't talk to each other.

**Solution:** Secrets are just thoughts with visibility rules. Access control is just attestations. Audit logs are just because chains.

**One-liner:** "Pool, Peer, Rules — three primitives that replace your keyvault, your ACL system, and your audit log."

**Angle for wot.rocks:** "Manage who sees what without a separate password manager. Your devices sync secrets automatically because they're in the same pool."

**Angle for wot.technology:** "Identity → Access Control Collapse. The same ed25519 keypair handles WoT identity, TLS client certs, IPv6 access grants, and Tor onion addresses."

---

### Trust-Weighted Search

**Problem:** "When I ran ChatGPT Deep Research on questions in my specific domain, it used low-quality random news stories as sources for its report." — PhD researcher with 15 years expertise

**Solution:** `relevance = similarity × trust`. Your trusted sources surface first. News aggregators drop below the waterline.

**One-liner:** "Expert beats noise even with lower similarity — because you told us who to trust."

**Angle for wot.rocks:** "Stop getting answers from strangers. Get answers from people you've chosen to trust."

**Angle for wot.technology:** "Trust-weighted RAG. The subconscious retrieves candidates by similarity. Working memory filters by trust. Only grounded content surfaces."

---

### Your Algorithm

**Problem:** "Dear Algo, please stop showing me humans moments before their death." Reactive, per-item, Sisyphean.

**Solution:** Aspects define what surfaces. Configure once, switch modes like gears.

**One-liner:** "'Dear Algo' becomes 'My Algo' — configuration, not plea."

**Angle for wot.rocks:** "Sunday morning mode: puppies, not politics. Monday crisis mode: show me everything. You decide."

**Angle for wot.technology:** "Attention sovereignty via aspect thoughts. Mode switching reconfigures salience weights. Same waterline model, different comfort level."

---

### Because Chains

**Problem:** AI says something. Where did it come from? Who verified it? What was the path?

**Solution:** Every thought links back to what caused it. Walk the chain to find the source.

**One-liner:** "If there's no because chain, it didn't happen."

**Angle for wot.rocks:** "Every answer shows you where it came from. Click through to the source. Trust or don't — your choice."

**Angle for wot.technology:** "Merkle DAG with because references. Trail walking is O(depth). Verify to trust anchors, not origin."

---

### Cold Start (Hello Handshake)

**Problem:** Two strangers, no prior chain, want to talk.

**Solution:** Out-of-band bootstrap (QR, email) + in-band verification. Private pool created. Trust starts at zero, grows from interaction.

**One-liner:** "Meet anyone. Trust nobody until they prove themselves."

**Angle for wot.rocks:** "Scan a QR code, verify cryptographically, start a private conversation. No platform in the middle."

**Angle for wot.technology:** "Hello cards with ed25519 signatures. Bilateral attestation creates shared pool. Trust grows from attestation history."

---

### Compromise Recovery

**Problem:** Phone stolen. Bad actor creates content in your name. How do you recover?

**Solution:** Revocation attestation + compromise window marker. Flagged content requires review. Old work stays trusted.

**One-liner:** "Data is immutable. Trust is recomputable."

**Angle for wot.rocks:** "Lose a device? Flag the suspect period. Your old work is still trusted. The compromised stuff gets quarantined."

**Angle for wot.technology:** "Revocation creates compromise_window aspect. All thoughts in window get 0.0 attestation via marker. Resolution options: reject (-1), verify (+1), investigate (0)."

---

### now.pub

**Problem:** Derek Sivers' /now pages (2015) hit limits: manual updates, no format, stale everywhere.

**Solution:** Machine-readable presence. Auto-stale if not refreshed. Ambient from trails.

**One-liner:** "What are you working on right now? now.pub knows."

**Angle for wot.rocks:** "Reserve your name. Let people know what you're up to. Bots too — queue depth, estimated wait."

**Angle for wot.technology:** "TTL thoughts auto-expire. Ambient generation from recent activity trails. IPNS resolution for stable naming."

---

## Comparisons

### vs Traditional RAG
| Traditional | WoT |
|-------------|-----|
| similarity(query, doc) | similarity × trust |
| SEO wins | Your experts win |
| No provenance | Full because chain |
| Same results for everyone | Your trust graph shapes results |

### vs Password Managers
| Password Manager | WoT Pool-Peer-Rules |
|------------------|---------------------|
| Separate system | Secrets are thoughts |
| Config files | Attestation thoughts |
| Audit logs | Because chains |
| Device sync | Pool membership |

### vs Current Social
| Twitter/X | WoT |
|-----------|-----|
| Their algo | Your algo |
| Block = invisible | Low trust = visible but discounted |
| No receipts | Full provenance |
| Platform controls | You control |

---

## Historical Anchors

**Kushim (3400 BCE):** First named person in history wasn't a king — was an accountant tracking beer ingredients. Writing started as receipts. Wellspring = receipts for cognition.

**Vannevar Bush (1945):** "As We May Think" described associative trails, bidirectional links, trail sharing. We're completing his vision with trust and AI.

**Halt and Catch Fire:** "Computers aren't the thing. They're the thing that gets us to the thing." WoT is infrastructure for cognition, not the cognition itself.

---

## External Validation

**@strickvl context rot post:** PhD with 15 years Afghanistan research. Deep Research gave him news articles. No expertise recognition. WoT answer: trust-weighted retrieval surfaces his verified sources first.

**BitNet slop thread:** AI post ratio'd for claiming Microsoft "FINALLY" open-sourced something that was open 2-3 years ago. WoT answer: attestation = skin in game. Either check facts or reputation takes hit.

**Grady Booch code provenance:** Claude imports libs unprompted. Dead code accumulates. "Asbestos in the walls." WoT answer: every commit has because chain. Empty attestation = doesn't merge.

---

## Landing Page Sections (wot.rocks)

1. **Hero:** "Your computer buddy. Your external brain. Your web of trust."
2. **Problem:** AI gives you average answers from strangers. You want expert answers from people you trust.
3. **Solution:** Track what you know, why you know it, and who told you. Same primitives, personal to planetary.
4. **How it works:** Capture → Index → Present → Attest → Learn → Publish
5. **Features:** Your algo, your receipts, your privacy, your network
6. **now.pub:** Reserve your name, broadcast your status
7. **Get started:** Email signup + subdomain reservation

---

*Last updated: 2026-01-31*
*Sources: wellspring-traces.md, wot-v0.7.md, wot-tracesv2.md*

---

## Domain Portfolio

| Domain | Current Use | Potential |
|--------|-------------|-----------|
| **wot.rocks** | Main landing | Consumer-friendly "why" |
| **wot.technology** | Tech docs | Developer "how" |
| **now.pub** | Identity namespace | Live presence/status |
| wot.digital | Held | Developer portal? API docs? |
| wot.mobi | Held | Mobile-first demo? PWA? |
| wot.services | Held | Service directory for protocol layer? |
| wotwot.uk | Held | UK presence / quirky branding |

**Brand hierarchy:**
- wot.rocks = front door (everyone)
- wot.technology = side door (developers)
- now.pub = live demo (see it working)
- wot.services = marketplace (when ecosystem grows)

---

## wot.services: Ingestion Layer

**Problem:** New user, empty graph. Nothing to search, nothing to attest.

**Solution:** Bring your digital exhaust. Email, bookmarks, notes, chat history → instant corpus.

### Sources We Convert

| Source | What You Get |
|--------|--------------|
| Email | Sender as identity, threads as chains |
| RSS | Feed items as thoughts |
| Podcasts | Transcribed + timestamped |
| WhatsApp/Slack | Chats as thought threads |
| Browser history | Where you've been |
| Notes (Obsidian/Notion) | Your PKM, now searchable |

### Tiers

- **Free:** 100 thoughts/day, basic sources
- **Pro:** 10k/day, all sources, private pools
- **Self-host:** Open source, unlimited, your infrastructure

**One-liner:** "Bring your history. We'll make it searchable, connected, and yours."

**Angle for wot.rocks:** "Already have years of email, notes, and bookmarks? Import them in minutes. Start with a full graph, not an empty one."

**Angle for wot.technology:** "Ingestion services as Docker containers. SMTP, RSS, chat exports. Push to your daemon via gRPC. Self-host or use our hosted tier."

---

## Mirror Trading via Trust

**Problem:** Copy-trading platforms pick "top traders" for you. Opaque track records, no rationale, platform takes a cut.

**Solution:** Follow traders you actually trust. Position size scales with trust. Full audit trail.

### How It's Different

| eToro Style | WoT Mirror |
|-------------|------------|
| Platform picks traders | You pick who to trust |
| Hidden rationale | Because chain shows why |
| Binary follow/unfollow | Trust score scales position |
| Platform custody | Your keys, your broker |

### Trust-Scaled Sizing

```
Trader says: 1% position
Your trust: 0.7
You execute: 0.7% position
```

New trader = tiny test positions. Proven trader = larger mirrors. Trust earned, not assumed.

**One-liner:** "Copy-trading without the platform. Follow who you trust, sized by how much."

**Angle for wot.rocks:** "Your friend's a great trader? Follow their moves automatically — sized by how much you trust them."

**Angle for wot.technology:** "Trade thoughts with because chains. Mirror execution with trust-scaled sizing. Full compliance audit trail."

---

## Commercialization: Trust-Weighted Signal Marketplace

**The thesis:** WoT enables trust-native signal marketplaces across any domain.

### Beyond Trading

| Domain | Signal | Outcome |
|--------|--------|---------|
| Investing | Trade calls | P&L |
| Hiring | Referrals | Retention |
| Purchasing | Recommendations | Satisfaction |
| Security | Threat intel | False positives |
| Research | Paper recs | Citations |

Same pattern everywhere: trusted source → signed signal → your rules → outcome → trust adjusts.

### Why It Wins

| Platform Model | WoT Model |
|----------------|-----------|
| Platform picks "top" performers | You pick who to trust |
| Opaque track records | Verifiable because chains |
| Platform takes cut | Direct peer relationship |
| Data locked in | Portable reputation |

### Revenue Layers

- **Signal subscriptions** — pay to access producer pools
- **Performance fees** — producer takes % of upside
- **Aggregation** — curate multiple sources, charge for the blend
- **Infrastructure** — host pools, thin margin
- **Validation oracles** — trusted outcome attesters

**One-liner:** "The protocol is the product. Everything else is services."

**Angle for investors:** "Network effects without lock-in. Reputation is portable, but the protocol is sticky."

---

## UK Property Chain Coordination

**Problem:** Property chains collapse because nobody sees the full picture. Everyone's playing telephone through solicitors.

**Solution:** Every party is an identity. Every milestone is an attested thought. Real-time chain health visible to all participants.

### Current vs WoT

| Current | WoT Chain |
|---------|-----------|
| Call solicitor, wait | Real-time status |
| "They said it's progressing" | Signed attestation |
| No visibility of other links | Full chain health |
| Gazumping surprises | Counter-offers visible |
| Blame game after collapse | Audit trail shows where it broke |

### Gazumping Prevention

Seller attests to offer lock. Breach = reputation hit. Future buyers see history.

Not legal enforcement — reputation enforcement.

**One-liner:** "See your property chain in real-time. Know where it's stuck. Never be surprised."

**Angle for wot.rocks:** "Buying a house? See every step of your chain — who's waiting on who, what's delayed, when it'll complete."

**Angle for estate agents:** "Stop chasing solicitors. Give clients real-time chain visibility. Stand out."

---

## Patient-Controlled Medical Records

**Problem:** Your medical records are scattered across systems you don't control. Sharing means "all or nothing." No visibility of who accessed what.

**Solution:** Your medical data in your pool. Create consultation-specific pools to share exactly what each provider needs. Full audit trail.

### How It Works

```
Your Medical Pool (private)
├── All your records, attested by providers
│
└── New consultation? Create a sharing pool:
    ├── Share: MRI, relevant blood work
    └── Don't share: unrelated history
```

### Key Features

| Current System | WoT Medical |
|----------------|-------------|
| Scattered across hospitals | Your pool, your control |
| Share all or nothing | Granular per-doctor |
| No access visibility | Full audit trail |
| Paper consent | Cryptographic attestation |

### Emergency Access

Pre-authorized pool with critical info only: blood type, allergies, medications. ER scans your ID, gets what they need, access logged.

### Provider Track Records

Doctors' diagnostic accuracy becomes computable from outcome attestations. Trust based on history, not credentials alone.

**One-liner:** "Your medical records. Your control. Share exactly what each doctor needs."

**Angle for wot.rocks:** "Seeing a new specialist? Share just the relevant records. Keep the rest private. Know exactly who accessed what."

**Angle for healthcare:** "GDPR portability built in. HIPAA audit trail automatic. Consent management via attestation."

---

## For the Sci-Fi Readers

### The Quantum Thief Connection

If you've read Hannu Rajaniemi's *The Quantum Thief*, you already understand WoT.

**Gevulot** — the Oubliette's cryptographic privacy system where you control what others perceive about you — is our visibility spectrum. `local_forever` to `null`, with pool boundaries in between.

**Exomemory** — external memory storage accessed via cryptographic protocols — is thoughts in pools.

**Jean le Flambeur's problem** — proving which copy of you is the real one — is exactly what proof of life ticks and watchdog pools solve.

*The difference:* Gevulot is centralized (the city runs it). WoT is distributed (you carry it with you).

Rajaniemi did the worldbuilding. We're writing the protocol.

### One-liner

> "Gevulot for the real world, but you don't need a walking Martian city to run it."

### The Anti-Torment Nexus

For those familiar with the [Torment Nexus meme](https://en.wikipedia.org/wiki/Torment_Nexus): we're aware.

But gevulot isn't the cautionary tale. It's the infrastructure that *works* in the Oubliette. The citizens control their own privacy. The system serves people.

We're not building the dystopia. We're building the part of the sci-fi that was actually good.
