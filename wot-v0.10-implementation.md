# Web of Thought (WoT) Implementation Notes v0.10

**Practical Guidance for Prototyping**

*wot.rocks · wot.technology · now.pub*

*February 2026*

---

## Abstract

Implementation notes for WoT prototype development. Language choices, storage strategies, indexer architecture, agent integration patterns, and lessons learned from testing.

---

## Part 1: Language & Runtime Strategy

### Rust Core + Multi-Target

```
┌─────────────────────────────────────────────────────┐
│              libwellspring (Rust)                   │
├─────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐ │
│  │ Native  │  │  WASM   │  │  WASM   │  │ Python │ │
│  │ daemon  │  │ browser │  │  edge   │  │ PyO3   │ │
│  └─────────┘  └─────────┘  └─────────┘  └────────┘ │
│       │            │            │            │      │
│   Desktop      Browser      Cloudflare    Jupyter  │
│   Mobile       Artifacts    Workers       Scripts  │
│   Server       Extensions   Deno Deploy            │
└─────────────────────────────────────────────────────┘
```

### Why Rust

| Concern | Rust Advantage |
|---------|----------------|
| Latency | Sub-μs salience checks |
| Memory | No GC pauses for daemons |
| Safety | Compile-time guarantees |
| Ecosystem | libp2p, iroh, SpacetimeDB patterns |
| WASM | Clean compilation |
| Serialization | serde (compile-time, zero-copy) |

### Core Dependencies

```toml
[dependencies]
# Crypto
blake3 = "1.5"
ed25519-dalek = "2.0"
chacha20poly1305 = "0.10"

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
ciborium = "0.2"  # CBOR

# Storage
rusqlite = { version = "0.31", features = ["bundled"] }
redb = "2.0"  # Alternative: embedded key-value

# Networking
libp2p = "0.53"
tokio = { version = "1.0", features = ["full"] }

# Indexing
tantivy = "0.21"  # Full-text search
fastembed = "3.0"  # Local embeddings
```

### WASM Considerations

Browser target restrictions:
- No filesystem (use IndexedDB)
- No raw sockets (use WebSocket/WebRTC)
- No threads (use Web Workers)

```rust
#[cfg(target_arch = "wasm32")]
use web_sys::IdbDatabase;

#[cfg(not(target_arch = "wasm32"))]
use rusqlite::Connection;
```

---

## Part 2: Storage Architecture

### Layered Storage

```
┌─────────────────────────────────────────┐
│  HOT LAYER (in-memory)                  │
│  - Recent thoughts (LRU cache)          │
│  - Active trust scores                  │
│  - Current context graph                │
├─────────────────────────────────────────┤
│  WARM LAYER (embedded DB)               │
│  - SQLite: structured queries           │
│  - Tantivy: full-text search            │
│  - Vector index: semantic similarity    │
├─────────────────────────────────────────┤
│  COLD LAYER (content-addressed)         │
│  - IPFS / local CID store               │
│  - Archival thoughts                    │
│  - Rarely accessed content              │
└─────────────────────────────────────────┘
```

### SQLite Schema

```sql
-- Core tables
CREATE TABLE thoughts (
    cid TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    content BLOB NOT NULL,  -- CBOR
    created_by TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    source TEXT,
    signature BLOB NOT NULL
);

CREATE TABLE because (
    thought_cid TEXT NOT NULL,
    ref_cid TEXT NOT NULL,
    ref_type TEXT,  -- 'full' | 'segment' | 'anchor'
    segment_cid TEXT,
    anchor_json TEXT,
    PRIMARY KEY (thought_cid, ref_cid)
);

CREATE TABLE connections (
    cid TEXT PRIMARY KEY,
    relation TEXT NOT NULL,
    from_cid TEXT NOT NULL,
    to_cid TEXT NOT NULL
);

CREATE TABLE attestations (
    cid TEXT PRIMARY KEY,
    on_cid TEXT NOT NULL,
    via_cid TEXT,
    weight REAL NOT NULL,
    created_by TEXT NOT NULL
);

-- Indexes for common queries
CREATE INDEX idx_thoughts_type ON thoughts(type);
CREATE INDEX idx_thoughts_created_by ON thoughts(created_by);
CREATE INDEX idx_thoughts_created_at ON thoughts(created_at);
CREATE INDEX idx_connections_from ON connections(from_cid);
CREATE INDEX idx_connections_to ON connections(to_cid);
CREATE INDEX idx_connections_relation ON connections(relation);
CREATE INDEX idx_attestations_on ON attestations(on_cid);
CREATE INDEX idx_attestations_by ON attestations(created_by);

-- FTS5 for full-text search
CREATE VIRTUAL TABLE thoughts_fts USING fts5(
    cid,
    content,
    content=thoughts,
    content_rowid=rowid
);
```

### CID Store

Simple file-based for prototype:

```
~/.wellspring/
├── thoughts/
│   ├── blake3/
│   │   ├── 5c/
│   │   │   └── ecc66b61e356cef45f35f5e3da679e8d335d7e224c08cddd2f3b7c680e4393
│   │   └── ...
│   └── sha256/
│       └── ...
├── index.db          # SQLite
├── vectors.idx       # Embedding index
├── identity.key      # Ed25519 private key (encrypted)
└── config.toml
```

### Vector Index

```rust
use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};

struct VectorIndex {
    model: TextEmbedding,
    index: hnsw::Hnsw<f32>,  // or usearch, or annoy
}

impl VectorIndex {
    fn embed(&self, text: &str) -> Vec<f32> {
        self.model.embed(vec![text], None).unwrap()[0].clone()
    }
    
    fn search(&self, query: &str, k: usize) -> Vec<(Cid, f32)> {
        let query_vec = self.embed(query);
        self.index.search(&query_vec, k)
    }
}
```

---

## Part 3: Because Indexer

### Purpose

Transform existing content → WoT format thoughts with provenance chains.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    BECAUSE INDEXER                       │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ Git Adapter │    │Wiki Adapter │    │Site Adapter │  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│         └──────────────────┼──────────────────┘          │
│                            ▼                             │
│                   ┌─────────────────┐                    │
│                   │  Transform Core │                    │
│                   │  - CID compute  │                    │
│                   │  - Chain build  │                    │
│                   └────────┬────────┘                    │
│                            ▼                             │
│                   ┌─────────────────┐                    │
│                   │  Thought Store  │                    │
│                   └────────┬────────┘                    │
│                            ▼                             │
│                   ┌─────────────────┐                    │
│                   │   MCP Server    │                    │
│                   └─────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### Git Adapter

Git is ideal first source — already has content addressing and parent chains.

```rust
pub struct GitAdapter {
    repo_path: PathBuf,
    identity_map: HashMap<String, Cid>,  // email → WoT identity
}

impl GitAdapter {
    fn commit_to_thought(&self, commit: &Commit) -> Thought {
        let content = ThoughtContent::GitCommit {
            message: commit.message().to_string(),
            files_changed: commit.tree_diff_stats(),
        };
        
        let because: Vec<ContentRef> = commit.parents()
            .map(|p| ContentRef::full(self.commit_cid(&p)))
            .collect();
        
        Thought {
            r#type: "git/commit".into(),
            content,
            created_by: self.identity_for(&commit.author()),
            created_at: commit.time().seconds() * 1000,
            source: Some(self.git_source_cid()),
            because,
            ..Default::default()
        }
    }
}
```

### Wiki Adapter

```rust
pub struct WikiAdapter {
    base_url: String,
    identity: Cid,  // Indexer's identity
}

impl WikiAdapter {
    fn page_to_thought(&self, page: &WikiPage) -> Thought {
        let because: Vec<ContentRef> = page.links()
            .filter_map(|link| self.resolve_link(link))
            .collect();
        
        Thought {
            r#type: "wiki/page".into(),
            content: ThoughtContent::WikiPage {
                title: page.title.clone(),
                body: page.content.clone(),
                categories: page.categories.clone(),
            },
            created_by: self.identity,
            source: Some(self.wiki_source_cid()),
            because,
            ..Default::default()
        }
    }
}
```

### Output Format

JSONL for compatibility:

```jsonl
{"cid":"cid:blake3:abc...","type":"git/commit","content":{"message":"feat: Add indexer"},...}
{"cid":"cid:blake3:def...","type":"git/commit","content":{"message":"fix: Handle edge case"},...}
```

---

## Part 4: Trust Computation

### Data Structures

```rust
struct TrustGraph {
    vouches: HashMap<Cid, Vec<(Cid, f32)>>,  // identity → [(vouched, weight)]
    attestations: HashMap<Cid, Vec<Attestation>>,  // thought → attestations
    cache: LruCache<(Cid, Cid), f32>,  // (from, to) → computed trust
}

impl TrustGraph {
    fn trust(&mut self, from: &Cid, to: &Cid, max_depth: usize) -> f32 {
        if let Some(&cached) = self.cache.get(&(*from, *to)) {
            return cached;
        }
        
        let score = self.compute_trust(from, to, max_depth, &mut HashSet::new());
        self.cache.put((*from, *to), score);
        score
    }
    
    fn compute_trust(
        &self,
        from: &Cid,
        to: &Cid,
        depth: usize,
        visited: &mut HashSet<Cid>,
    ) -> f32 {
        if from == to { return 1.0; }
        if depth == 0 || visited.contains(from) { return 0.0; }
        
        visited.insert(*from);
        
        let Some(vouches) = self.vouches.get(from) else {
            return 0.0;
        };
        
        // Direct vouch
        if let Some((_, weight)) = vouches.iter().find(|(id, _)| id == to) {
            return *weight;
        }
        
        // Transitive (decay 0.5 per hop)
        const DECAY: f32 = 0.5;
        vouches.iter()
            .map(|(intermediate, weight)| {
                weight * DECAY * self.compute_trust(intermediate, to, depth - 1, visited)
            })
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0)
    }
}
```

### Groundedness

```rust
fn groundedness(&self, thought: &Thought, depth: usize) -> f32 {
    if thought.because.is_empty() {
        return 0.2;  // Base groundedness for terminal nodes
    }
    
    if depth == 0 {
        return 0.5;  // Don't recurse forever
    }
    
    let scores: Vec<f32> = thought.because.iter()
        .filter_map(|ref_| self.get_thought(&ref_.thought_cid))
        .map(|t| self.groundedness(&t, depth - 1))
        .collect();
    
    if scores.is_empty() {
        return 0.2;
    }
    
    // Average of because groundedness, slight boost for multiple sources
    let avg = scores.iter().sum::<f32>() / scores.len() as f32;
    let breadth_bonus = (scores.len() as f32).ln() * 0.1;
    (avg + breadth_bonus).min(1.0)
}
```

---

## Part 5: Salience & Waterline

### Heat Model (Ebbinghaus-Informed)

```rust
fn heat(&self, thought: &Thought, now: i64) -> f32 {
    let checkpoints = self.get_checkpoints(&thought.cid);
    
    let review_count = checkpoints.len();
    let last_access = checkpoints.iter()
        .map(|c| c.timestamp)
        .max()
        .unwrap_or(thought.created_at);
    
    let age_hours = (now - last_access) as f32 / 3_600_000.0;
    
    // Decay flattens with reviews (Ebbinghaus)
    let decay_rate = 0.1 / (1.0 + review_count as f32 * 0.5);
    
    (-decay_rate * age_hours).exp()
}
```

### Salience Formula

```rust
fn salience(&self, thought: &Thought, context: &Context) -> f32 {
    let reachability = self.reachability(thought, context);
    let confidence = self.path_confidence(thought, context);
    let heat = self.heat(thought, context.now);
    let belief = self.my_attestation_weight(thought);
    
    reachability * confidence * heat * belief.unwrap_or(0.5)
}
```

### Waterline

```rust
struct Waterline {
    threshold: f32,
    context: Context,
}

impl Waterline {
    fn above(&self, thoughts: &[Thought]) -> Vec<&Thought> {
        let mut scored: Vec<_> = thoughts.iter()
            .map(|t| (t, self.salience(t)))
            .filter(|(_, s)| *s >= self.threshold)
            .collect();
        
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        scored.into_iter().map(|(t, _)| t).collect()
    }
}
```

---

## Part 6: Sync Implementation

### Bloom Filter Exchange

```rust
use probabilistic_collections::bloom::BloomFilter;

struct SyncState {
    filter: BloomFilter<Cid>,
    since: i64,
}

impl SyncState {
    fn new(thoughts: &[Thought], since: i64) -> Self {
        let mut filter = BloomFilter::with_rate(0.01, thoughts.len());
        for t in thoughts.iter().filter(|t| t.created_at >= since) {
            filter.insert(&t.cid);
        }
        Self { filter, since }
    }
    
    fn diff(&self, other: &Self) -> (Vec<Cid>, Vec<Cid>) {
        // (they_have_we_dont, we_have_they_dont)
        // Requires actual CID lists after bloom negotiation
        todo!()
    }
}
```

### P2P Connection

```rust
use libp2p::{swarm::Swarm, PeerId};

struct WotNode {
    swarm: Swarm<WotBehavior>,
    store: ThoughtStore,
    trust: TrustGraph,
}

impl WotNode {
    async fn sync_with(&mut self, peer: PeerId) -> Result<SyncStats> {
        // Only sync with trusted peers
        let trust = self.trust.trust(&self.identity, &peer_identity);
        if trust < 0.3 {
            return Err(SyncError::InsufficientTrust);
        }
        
        // Exchange bloom filters
        let our_filter = self.store.bloom_filter(Duration::hours(24));
        let their_filter = self.request_filter(peer).await?;
        
        // Identify deltas
        let to_request = self.store.cids_not_in(&their_filter);
        let to_send = self.request_deltas(peer, to_request).await?;
        
        // Verify and merge
        for thought in to_send {
            if self.verify(&thought)? {
                self.store.insert(thought)?;
            }
        }
        
        Ok(SyncStats { received: to_send.len(), sent: to_request.len() })
    }
}
```

---

## Part 7: Agent Architecture

### Three Layers

```rust
struct AgentStack {
    conscious: ConsciousLayer,      // Full context, decisions
    working: WorkingMemoryLayer,    // Active research/debate
    subconscious: SubconsciousLayer, // Fast retrieval, no authority
}

struct SubconsciousLayer {
    vector_index: VectorIndex,
    bloom_filter: BloomFilter<Cid>,
    trust_cache: LruCache<Cid, f32>,
}

impl SubconsciousLayer {
    fn retrieve(&self, query: &str, limit: usize) -> Vec<Cid> {
        // Fast, cheap, no attestation authority
        self.vector_index.search(query, limit * 3)
            .into_iter()
            .filter(|(cid, _)| self.trust_cache.get(cid).unwrap_or(&0.0) > &0.3)
            .take(limit)
            .map(|(cid, _)| cid)
            .collect()
    }
}

struct ConsciousLayer {
    context_window: Vec<Thought>,
    current_focus: Option<Cid>,
    identity: Cid,
}

impl ConsciousLayer {
    fn attest(&self, thought: &Thought, weight: f32) -> Attestation {
        // Has authority to attest
        Attestation {
            on: thought.cid,
            via: None,
            weight,
            created_by: self.identity,
            ..Default::default()
        }
    }
}
```

### Context Injection

```rust
async fn prepare_context(
    &self,
    query: &str,
    max_thoughts: usize,
) -> Vec<Thought> {
    // 1. Subconscious retrieval (fast)
    let candidates = self.subconscious.retrieve(query, max_thoughts * 5);
    
    // 2. Working memory filter (recency, active threads)
    let filtered = self.working.filter_relevant(&candidates, query);
    
    // 3. Trust verification (slower, thorough)
    let verified: Vec<_> = filtered.into_iter()
        .filter(|cid| self.verify_trust(cid) > 0.5)
        .take(max_thoughts)
        .collect();
    
    // 4. Load full thoughts
    verified.into_iter()
        .filter_map(|cid| self.store.get(&cid))
        .collect()
}
```

---

## Part 8: Testing Strategy

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    #[test]
    fn cid_deterministic() {
        let thought = Thought { /* ... */ };
        let cid1 = compute_cid(&thought);
        let cid2 = compute_cid(&thought);
        assert_eq!(cid1, cid2);
    }
    
    #[test]
    fn trust_decays_with_distance() {
        let mut graph = TrustGraph::new();
        graph.add_vouch(a, b, 0.9);
        graph.add_vouch(b, c, 0.8);
        
        let direct = graph.trust(&a, &b, 3);
        let transitive = graph.trust(&a, &c, 3);
        
        assert!(direct > transitive);
        assert!(transitive < direct * 0.8 * 0.5);  // decay
    }
    
    #[test]
    fn revocation_propagates() {
        let mut graph = TrustGraph::new();
        graph.add_vouch(a, b, 0.9);
        graph.add_vouch(b, c, 0.8);
        
        let before = graph.trust(&a, &c, 3);
        graph.revoke_vouch(a, b);
        let after = graph.trust(&a, &c, 3);
        
        assert!(before > 0.0);
        assert_eq!(after, 0.0);
    }
}
```

### Integration Tests

```rust
#[tokio::test]
async fn index_git_repo() {
    let adapter = GitAdapter::new("./test-repo");
    let thoughts = adapter.index_all().await.unwrap();
    
    assert!(thoughts.len() > 0);
    
    // Verify because chains
    for thought in &thoughts {
        if thought.r#type == "git/commit" {
            // Non-root commits should have parents
            let commit = get_commit(&thought);
            if !commit.parents().is_empty() {
                assert!(!thought.because.is_empty());
            }
        }
    }
}
```

### Corpus Tests

```rust
#[test]
fn query_wot_spec() {
    let store = index_directory("./wot-spec");
    
    let results = store.search("visibility field removed");
    assert!(results.iter().any(|t| t.content.contains("v0.8")));
    
    // Walk because chain
    let spec_thought = results[0];
    let chain = store.walk_because(&spec_thought.cid, 5);
    assert!(chain.len() > 1);  // Has provenance
}
```

---

## Part 9: Performance Targets

### Latency Budgets

| Operation | Target | Notes |
|-----------|--------|-------|
| Salience check | < 100μs | Hot path, in-memory |
| Trust lookup (cached) | < 1μs | LRU cache hit |
| Trust computation | < 10ms | 3-hop traversal |
| Vector search | < 50ms | Top 50 results |
| Thought retrieval | < 1ms | SQLite lookup |
| Sync negotiation | < 100ms | Bloom exchange |

### Memory Budgets

| Component | Target |
|-----------|--------|
| Hot cache | 100MB |
| Vector index | 500MB (100k thoughts) |
| Bloom filter | 1MB |
| Trust cache | 10MB |

### Storage

| Metric | Target |
|--------|--------|
| Overhead per thought | < 100 bytes |
| Index ratio | < 2x content size |
| Sync delta | < 10% of changed content |

---

## Part 10: 12-Day Sprint

**Goal:** Working prototype that proves the thesis. People can use it. Peers can connect.

### Day 1-2: Core Working

- [ ] Thought struct + CID computation (BLAKE3)
- [ ] SQLite storage (single file, portable)
- [ ] Identity creation + signing
- [ ] `wot init` / `wot create` / `wot show` CLI
- [ ] JSONL import/export

**Exit criteria:** Can create thoughts, compute CIDs, store, retrieve.

### Day 3-4: Connections + Attestations

- [ ] Connection thoughts (from/to/relation)
- [ ] Attestation thoughts (on/weight)
- [ ] `wot connect` / `wot attest` CLI
- [ ] Basic trust computation (direct vouches only)
- [ ] Pool thoughts + `published_to` pattern

**Exit criteria:** Can build a graph. Can attest. Access model works.

### Day 5-6: Indexer + MCP

- [ ] Git adapter (commits → thoughts with because chains)
- [ ] MCP server (search, get, walk_because)
- [ ] Index this repo as test corpus
- [ ] Claude Code can query the graph

**Exit criteria:** Claude Code on SSH has context from indexed thoughts.

### Day 7-8: Sync MVP

- [ ] HTTP sync endpoint (not P2P yet — ship fast)
- [ ] Bloom filter negotiation
- [ ] Delta transfer (thoughts + connections + attestations)
- [ ] `wot sync <peer_url>` CLI

**Exit criteria:** Two machines can sync a pool.

### Day 9-10: Device Mesh

- [ ] Personal devices pool pattern
- [ ] Relay as optional backstop (simple HTTP relay)
- [ ] Basic conflict handling (latest timestamp wins)
- [ ] `wot daemon` for background sync

**Exit criteria:** Your devices stay in sync. Works offline, syncs when connected.

### Day 11: Polish + Deploy

- [ ] Docker image (`docker run wellspring/0.9`)
- [ ] Relay hosted somewhere (fly.io or similar)
- [ ] README with 5-minute quickstart
- [ ] Record demo GIF

**Exit criteria:** Someone else can run it.

### Day 12: Launch

- [ ] Announce (HN, Twitter, relevant communities)
- [ ] Respond to early feedback
- [ ] Document the sharp edges
- [ ] Tag v0.9.0

---

### What's CUT (do later)

- P2P (libp2p) — HTTP sync is fine for now
- WASM browser build — desktop first
- Vector embeddings — FTS5 is enough, structural retrieval first
- Salience/waterline — manual query is fine
- Full trust decay — direct vouches only
- Key rotation/recovery — single device identity first
- Private checkpoints — later
- now.pub integration — later

### What's SPECIFIED but not yet BUILT (v0.10 schema layer)

- Attestation-triggered content delivery (Part 11)
- Attention requests with trust-weighted urgency (Part 12)
- Core response schemas with inheritance (Part 12)
- Encrypted storage with layered keys (Part 13)
- Timed access / ephemeral keys (Part 13)
- Per-identity content key wrapping (Part 13)
- Structural retrieval / PageIndex pattern (Part 14)
- Schema-driven delivery modes

### The Bet

Everyone else is building complexity. We ship simplicity:
- One primitive
- It works in a text file
- Grows to a network
- Same format, same receipts

The race isn't to most features. It's to clearest value prop that actually runs.

---

## Lessons Learned

### From Testing

1. **CID stability**: Canonical JSON is critical. Key order matters.

2. **Trust cycles**: Graph can have cycles in vouches. Visited set required.

3. **Because depth**: Unbounded recursion kills performance. Cap at 5-7 hops.

4. **Attestation accumulation**: Thousands of attestations on popular thoughts. Index critical.

5. **Bloom false positives**: 1% FPR is fine. 10% causes sync thrashing.

### From Prior Art

**SpacetimeDB patterns to adopt:**
- SQL subscriptions → aspect/trust filter subscriptions
- Delta computation → only sync changes
- Client-side cache → local graph as truth
- Reducers → attestation is only mutation

**Google Wave lessons:**
- Simple primitive beats complex product
- Protocol survives, products die
- "What IS it?" kills adoption — be specific

### Open Issues

1. **Query language**: SQL-ish? GraphQL? Custom DSL?

2. **Schema migration**: How to evolve schemas without breaking CIDs?

3. **Key rotation UX**: Social recovery is complex. Simplify?

4. **Mobile battery**: Sync frequency vs battery life tradeoff.

5. **Large content**: Thoughts with multi-MB content. Chunk or reference?

---

## Part 11: Attestation-Triggered Content Delivery

### The Pattern

Not everything syncs eagerly. For large content (video, audio, datasets), attestation acts as a pull request.

```
BROWSE (metadata key M):
  → See what exists in pool
  → Titles, durations, thumbnails, connections
  → No content transferred yet

ATTEST (interest):
  → "I want to consume this"
  → Triggers content sync/stream
  → Schema determines delivery method

CONSUME:
  → Content flows
  → Checkpoint tracks engagement
  → Private, as always
```

### Interest Attestation

```json
{
  "type": "attestation",
  "content": {
    "on": "cid:blake3:video_thought",
    "via": "cid:blake3:aspect_ready_to_consume",
    "weight": 1.0
  },
  "created_by": "viewer_identity"
}
```

Weight semantics for consumption:

| Weight | Meaning |
|--------|---------|
| 1.0 | Stream now |
| 0.5 | Queue / download when convenient |
| 0.0 | Cancel / no longer interested |
| -1.0 | Remove from my graph |

### Schema-Driven Delivery Hints

Schemas define HOW content flows when requested:

```json
{
  "type": "schema",
  "content": {
    "name": "video/episode",
    "fields": {
      "title": { "type": "string" },
      "duration_ms": { "type": "integer" },
      "thumbnail": { "type": "cid" },
      "media": { "type": "bytes" }
    },
    "delivery": {
      "media": {
        "mode": "stream",
        "chunk_size": 2097152,
        "codec": "av1",
        "adaptive": true
      },
      "thumbnail": {
        "mode": "eager",
        "max_bytes": 65536
      }
    }
  }
}
```

### Delivery Modes

| Mode | Behavior | Use For |
|------|----------|---------|
| `eager` | Sync immediately with metadata | Thumbnails, titles, small assets |
| `lazy` | Fetch on first access | Documents, images |
| `stream` | Progressive delivery on attestation | Video, audio, large datasets |
| `reference` | CID only, never auto-fetch | External content, optional resources |

### The Full Flow

```
CREATOR publishes video:
  1. Thought: video metadata (title, duration, thumbnail)
  2. Connection: published_to → pool
  3. Thumbnail: eager delivery (comes with metadata)
  4. Media: stream mode (waits for attestation)

VIEWER browses pool (has metadata key M):
  1. Sees: titles, thumbnails, durations, connections
  2. Sees: who created, attestation counts, trust scores
  3. Does NOT have: actual video content yet

VIEWER attests interest:
  1. Creates attestation: weight 1.0, via ready_to_consume aspect
  2. Attestation syncs to content holders
  3. Content holders begin streaming to viewer
  4. Schema rules: chunk_size, codec, adaptive bitrate

VIEWER watches:
  5. Private checkpoint tracks: time watched, paused, rewatched
  6. Checkpoint never syncs (attention sovereignty)
  7. Optional: public attestation after viewing (review/rating)
```

### Adaptive Delivery

Schema can specify adaptive rules:

```json
{
  "delivery": {
    "media": {
      "mode": "stream",
      "adaptive": true,
      "quality_levels": [
        { "resolution": "360p", "bitrate": 500000 },
        { "resolution": "720p", "bitrate": 1500000 },
        { "resolution": "1080p", "bitrate": 4000000 }
      ],
      "initial_buffer_ms": 5000
    }
  }
}
```

### Content Type Examples

**Video (YouTube-like):**
```
Schema: video/episode
  eager:  thumbnail, title, duration, creator
  stream: media (on attestation)
  
Pool: "keif-film-archive"
  Viewer browses → sees catalog
  Attests interest → stream begins
```

**Music (Spotify-like):**
```
Schema: audio/track
  eager:  title, artist, album_art, duration
  stream: audio (on attestation)
  lazy:   lyrics
```

**Dataset (research):**
```
Schema: data/tabular
  eager:  description, row_count, column_names, sample_rows
  lazy:   full dataset (on attestation)
  
Researcher sees metadata → decides → attests → downloads
```

**Live stream:**
```
Schema: video/live
  eager:  title, streamer, status
  stream: media (continuous while attested)
  
Attest weight 0.0 → stop streaming to you
```

### Why This Works

| YouTube | WoT |
|---------|-----|
| Algorithm decides what you see | Trust graph + your attestations |
| Platform stores all content | Peers hold content |
| You watch what's pushed | You pull what you attest |
| Engagement tracked, sold | Engagement private, yours |
| Creator at platform's mercy | Creator controls pool governance |
| Demonetization | Direct attestation-based economics |

### Economic Layer (Future)

Attestation can carry payment commitment:

```json
{
  "type": "attestation",
  "content": {
    "on": "video_thought_cid",
    "via": "aspect/ready_to_consume",
    "weight": 1.0
  },
  "because": ["payment_channel_cid"]
}
```

`because` points to payment proof. Creator verifies before streaming. No platform cut.

---

## Part 12: Attention Requests

### The Pattern

Directed request for a specific identity to engage with a thought or thread. Trust-weighted @-mention with protocol-level semantics.

```
CONNECTION: thought_cid → request_attention → target_identity_cid
    signed by: requester
    because: [why this matters]
```

### Three Attestation-Driven Patterns

| Pattern | Via Aspect | Direction | Triggers |
|---------|-----------|-----------|----------|
| Trust signal | `agreement` | About a thought | Trust computation |
| Content delivery | `ready_to_consume` | Self → content | Streaming/sync |
| Attention request | `request_attention` | Thought → identity | Surfacing/caching |

### Structure

```json
{
  "type": "connection",
  "content": {
    "relation": "request_attention",
    "from": "cid:blake3:thought_to_surface",
    "to": "cid:blake3:target_identity"
  },
  "created_by": "requester_identity",
  "because": ["cid:blake3:context_for_why"]
}
```

Optional urgency attestation on the connection:

```json
{
  "type": "attestation",
  "content": {
    "on": "cid:blake3:the_attention_request_connection",
    "weight": 0.8
  }
}
```

### Weight as Urgency

| Weight | Recipient Daemon Behavior |
|--------|---------------------------|
| 0.1–0.3 | Warm into subconscious (pre-cache, no notification) |
| 0.4–0.6 | Surface in working memory (next session, ambient awareness) |
| 0.7–0.9 | Active notification (review requested) |
| 1.0 | Interrupt (urgent, time-sensitive) |

### Recipient Processing

```rust
async fn handle_attention_request(
    &self,
    request: &Connection,
    attestation: &Attestation,
) -> Result<()> {
    // 1. Trust gate — do I trust the requester?
    let requester_trust = self.trust_graph
        .trust(&self.identity, &request.created_by, 3);
    
    if requester_trust < self.attention_threshold {
        return Ok(());  // Silent ignore, below trust threshold
    }
    
    // 2. Effective urgency = weight × requester trust
    let urgency = attestation.weight * requester_trust;
    
    // 3. Route by urgency
    match urgency {
        u if u < 0.3 => {
            // Pre-cache: warm the thought into local index
            self.subconscious.pre_cache(&request.from).await?;
        }
        u if u < 0.7 => {
            // Working memory: surface next session
            self.working_memory.queue(&request.from, urgency).await?;
        }
        _ => {
            // Conscious: active notification
            self.notify(&request.from, &request.created_by, urgency).await?;
        }
    }
    
    Ok(())
}
```

### Response Patterns

Response to any thought is an attestation. Valid responses defined by the target thought's schema.

**Default attention response schema:**

```json
{
  "type": "schema",
  "content": {
    "name": "response/attention",
    "responses": ["seen", "acted", "denied", "ignored"],
    "fields": {
      "status": { "type": "enum", "values": ["seen", "acted", "denied", "ignored"] },
      "note": { "type": "string", "required": false }
    }
  }
}
```

**Attestation carries the response:**

```json
{
  "type": "attestation",
  "content": {
    "on": "cid:blake3:attention_request",
    "via": "cid:blake3:schema/response/attention",
    "weight": 0.5
  },
  "because": ["cid:blake3:response_detail_thought"]
}
```

**Schema-appropriate responses — any thought type defines its own:**

| Schema | Valid Responses | Example |
|--------|----------------|---------|
| `response/attention` | seen, acted, denied, ignored | @mention |
| `response/review` | approved, changes_requested, commented | Code review |
| `response/invitation` | accepted, declined, tentative | Pool invite |
| `response/proposal` | endorsed, blocked, abstained | Governance |
| `response/incident` | acknowledged, escalated, resolved | On-call alert |
| `response/delivery` | received, rejected, partial | Content stream |

**The pattern:**

```
Any thought
  ↓ has schema
Schema defines valid responses
  ↓
Attestation via response schema = typed reply
  ↓
Weight still carries signal:
  +1.0 = strong positive (approved, endorsed)
   0.0 = neutral (seen, abstained)
  -1.0 = strong negative (denied, blocked)
```

No special-casing. The response vocabulary belongs to the schema, not the protocol.

### Core Response Schemas (Bootstrap)

Pre-defined in the library pool. Can't cold-start without these.

**Universal (applies to any thought):**

```json
{
  "type": "schema",
  "content": {
    "name": "response/universal",
    "responses": {
      "seen":    { "weight": 0.0, "meaning": "Acknowledged receipt" },
      "acted":   { "weight": 1.0, "meaning": "Engaged meaningfully" },
      "denied":  { "weight": -1.0, "meaning": "Rejected / refused" },
      "ignored": { "weight": null, "meaning": "Explicit no-engagement (absence of attestation is implicit)" }
    }
  }
}
```

**Attention:**

```json
{
  "name": "response/attention",
  "extends": "response/universal",
  "responses": {
    "deferred": { "weight": 0.1, "meaning": "Not now, remind later" },
    "delegated": { "weight": 0.5, "meaning": "Passed to someone else", "requires": ["delegated_to"] }
  }
}
```

**Review:**

```json
{
  "name": "response/review",
  "extends": "response/universal",
  "responses": {
    "approved":           { "weight": 1.0 },
    "changes_requested":  { "weight": -0.5, "requires": ["rework_suggestion"] },
    "commented":          { "weight": 0.3 }
  }
}
```

**Governance:**

```json
{
  "name": "response/governance",
  "extends": "response/universal",
  "responses": {
    "endorsed":  { "weight": 1.0 },
    "blocked":   { "weight": -1.0, "requires": ["because"] },
    "abstained": { "weight": 0.0 }
  }
}
```

**Delivery:**

```json
{
  "name": "response/delivery",
  "extends": "response/universal",
  "responses": {
    "received":  { "weight": 1.0 },
    "rejected":  { "weight": -1.0 },
    "partial":   { "weight": 0.5 },
    "corrupted": { "weight": -1.0, "requires": ["expected_cid"] }
  }
}
```

**Invitation:**

```json
{
  "name": "response/invitation",
  "extends": "response/universal",
  "responses": {
    "accepted":   { "weight": 1.0 },
    "declined":   { "weight": -1.0 },
    "tentative":  { "weight": 0.3 },
    "expired":    { "weight": 0.0 }
  }
}
```

### Schema Inheritance

`extends` means: inherit parent responses + add new ones.

```
response/universal         ← always available
  ├── response/attention   ← adds: deferred, delegated
  ├── response/review      ← adds: approved, changes_requested, commented
  ├── response/governance  ← adds: endorsed, blocked, abstained
  ├── response/delivery    ← adds: received, rejected, partial, corrupted
  └── response/invitation  ← adds: accepted, declined, tentative, expired
```

Every response schema includes `seen`, `acted`, `denied`, `ignored` from universal. You can always fall back to basics.

### Custom Response Schemas

Anyone can create domain-specific responses that extend the core:

```json
{
  "name": "response/medical_triage",
  "extends": "response/attention",
  "responses": {
    "emergent":    { "weight": 1.0, "meaning": "Immediate intervention" },
    "urgent":      { "weight": 0.8 },
    "non_urgent":  { "weight": 0.3 },
    "discharged":  { "weight": -0.5 }
  }
}
```

Extends attention (which extends universal). Full chain: `discharged` from medical, `deferred` from attention, `seen` from universal — all valid responses.

### Use Cases

| Scenario | From → To | Weight | Effect |
|----------|-----------|--------|--------|
| Code review request | PR thought → reviewer | 0.7 | Surfaces for review |
| FYI, no action needed | article → colleague | 0.2 | Warms into their context |
| Urgent incident | alert → on-call | 1.0 | Interrupts |
| AI agent needs human | decision_point → human | 0.8 | Human-in-the-loop |
| Recommended reading | book → friend | 0.3 | Ambient awareness |

### Spam Prevention

Trust threshold gates everything:

```
Stranger (trust 0.0) × urgency 1.0 = effective 0.0 → ignored
Trusted colleague (trust 0.9) × urgency 0.5 = effective 0.45 → surfaces
Close friend (trust 1.0) × urgency 0.3 = effective 0.3 → pre-cached
```

No trust = no attention. Earned trust = earned attention.

### Thread Awareness

Request attention on a connection (not just a thought):

```json
{
  "type": "connection",
  "content": {
    "relation": "request_attention",
    "from": "cid:blake3:connection_that_links_thread",
    "to": "cid:blake3:target_identity"
  }
}
```

"Look at this RELATIONSHIP between these thoughts" — not just the thought, but the structure. Recipient's daemon walks the connection to understand the thread.

---

## Part 13: Encrypted Storage (Share-Nothing Persistence)

### The Pattern

```
┌─────────────────────────────────────────────────────┐
│  YOUR DEVICE                                        │
│  ┌─────────────┐                                    │
│  │   Thought   │                                    │
│  │  (cleartext)│                                    │
│  └──────┬──────┘                                    │
│         ↓                                           │
│  ┌─────────────┐                                    │
│  │  Encrypt    │  ← Pool key (ChaCha20-Poly1305)   │
│  └──────┬──────┘                                    │
│         ↓                                           │
│  ┌─────────────┐                                    │
│  │   CID →     │                                    │
│  │   Blob      │                                    │
│  └──────┬──────┘                                    │
└─────────┼───────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────┐
│  STORAGE BACKEND (Dropbox, S3, NAS, friend's box)   │
│                                                     │
│  Sees:  cid:blake3:abc... → [encrypted bytes]       │
│  Knows: nothing                                     │
│  Can:   store, retrieve, delete                     │
│  Cannot: read, decrypt, understand structure        │
└─────────────────────────────────────────────────────┘
```

### Pool Key Derivation

```rust
fn derive_pool_key(pool_identity: &Ed25519PrivateKey) -> ChaCha20Key {
    // X25519 for encryption (derived from ed25519)
    let x25519_secret = pool_identity.to_x25519();
    
    // HKDF for key derivation
    let hkdf = Hkdf::<Sha256>::new(
        Some(b"wot-pool-encryption-v1"),
        x25519_secret.as_bytes()
    );
    
    let mut key = [0u8; 32];
    hkdf.expand(b"chacha20-poly1305", &mut key).unwrap();
    ChaCha20Key::from(key)
}
```

### Encrypted Thought Format

```rust
struct EncryptedThought {
    cid: Cid,                    // CID of cleartext (for verification after decrypt)
    nonce: [u8; 12],             // ChaCha20 nonce (random per thought)
    ciphertext: Vec<u8>,         // Encrypted CBOR
    tag: [u8; 16],               // Poly1305 auth tag
}

impl EncryptedThought {
    fn encrypt(thought: &Thought, pool_key: &ChaCha20Key) -> Self {
        let cleartext = thought.to_cbor();
        let cid = compute_cid(&cleartext);
        
        let nonce = random_nonce();
        let cipher = ChaCha20Poly1305::new(pool_key);
        let ciphertext = cipher.encrypt(&nonce, cleartext.as_ref()).unwrap();
        
        Self { cid, nonce, ciphertext, tag: /* from ciphertext */ }
    }
    
    fn decrypt(&self, pool_key: &ChaCha20Key) -> Result<Thought> {
        let cipher = ChaCha20Poly1305::new(pool_key);
        let cleartext = cipher.decrypt(&self.nonce, self.ciphertext.as_ref())?;
        
        let thought = Thought::from_cbor(&cleartext)?;
        
        // Verify CID matches
        if compute_cid(&cleartext) != self.cid {
            return Err(Error::CidMismatch);
        }
        
        Ok(thought)
    }
}
```

### Storage Backend Interface

```rust
trait BlobStorage {
    async fn put(&self, cid: &Cid, blob: &[u8]) -> Result<()>;
    async fn get(&self, cid: &Cid) -> Result<Vec<u8>>;
    async fn delete(&self, cid: &Cid) -> Result<()>;
    async fn list(&self, prefix: Option<&str>) -> Result<Vec<Cid>>;
}

// Implementations for various backends
struct S3Storage { bucket: String, client: S3Client }
struct DropboxStorage { token: String }
struct LocalStorage { path: PathBuf }
struct FriendNasStorage { ssh_config: SshConfig }
```

### Key Distribution

New member joining private pool:

```rust
async fn invite_to_pool(
    &self,
    pool: &Pool,
    invitee: &Identity,
) -> Result<PoolInvitation> {
    // 1. Verify we have authority to invite
    self.verify_invite_permission(pool)?;
    
    // 2. Create invitation thought
    let invitation = Thought::new_invitation(pool, invitee);
    
    // 3. Encrypt pool key for invitee's public key
    let encrypted_key = self.encrypt_for(
        &pool.encryption_key(),
        &invitee.pubkey
    );
    
    // 4. Send via secure channel (existing E2E or out-of-band)
    Ok(PoolInvitation {
        pool_cid: pool.cid,
        encrypted_key,
        invitation_thought: invitation.cid,
    })
}
```

### Key Rotation on Revocation

```rust
async fn revoke_member(&self, pool: &Pool, member: &Identity) -> Result<()> {
    // 1. Remove membership attestation
    self.revoke_attestation(pool, member)?;
    
    // 2. Generate new pool key
    let new_key = generate_pool_key();
    
    // 3. Re-encrypt all pool thoughts with new key
    // (Can be done lazily on next access)
    self.schedule_reencryption(pool, new_key)?;
    
    // 4. Distribute new key to remaining members
    for remaining in pool.members().filter(|m| m != member) {
        self.send_new_key(remaining, new_key)?;
    }
    
    // Note: Revoked member retains access to historical content
    // they already decrypted. This is unavoidable.
    
    Ok(())
}
```

### Layered Encryption (Metadata vs Content)

Separate keys for structure and content enables privacy-preserving indexing:

```
┌─────────────────────────────────────────────────────┐
│  THOUGHT                                            │
├─────────────────────────────────────────────────────┤
│  METADATA LAYER (Key M)                             │
│  ├── cid                                            │
│  ├── type                                           │
│  ├── created_by (or encrypted identity)             │
│  ├── created_at                                     │
│  ├── source (CID ref)                               │
│  ├── because (CID refs only, not content)           │
│  └── connection targets (CIDs)                      │
├─────────────────────────────────────────────────────┤
│  CONTENT LAYER (Key C)                              │
│  └── actual payload (encrypted separately)          │
└─────────────────────────────────────────────────────┘
```

**Access levels:**

| Role | Keys | Can See |
|------|------|---------|
| Storage backend | None | Encrypted blobs |
| Structural indexer | M | Graph structure, types, relations |
| Full member | M + C | Everything |

### Encrypted Thought with Layers

```rust
struct LayeredEncryptedThought {
    cid: Cid,  // Of full cleartext (for verification)
    
    // Metadata layer - indexers can decrypt this
    metadata_nonce: [u8; 12],
    metadata_ciphertext: Vec<u8>,  // Encrypted: type, timestamps, CID refs
    metadata_tag: [u8; 16],
    
    // Content layer - members only
    content_nonce: [u8; 12],
    content_ciphertext: Vec<u8>,  // Encrypted: actual payload
    content_tag: [u8; 16],
}

#[derive(Serialize, Deserialize)]
struct ThoughtMetadata {
    r#type: String,
    created_by: Cid,
    created_at: i64,
    source: Option<Cid>,
    because: Vec<Cid>,  // CID refs only, no ContentRef details
    connections: Vec<ConnectionSummary>,
}

#[derive(Serialize, Deserialize)]
struct ConnectionSummary {
    relation: String,
    to: Cid,
}
```

### Key Distribution

```rust
struct PoolKeys {
    metadata_key: ChaCha20Key,  // Share with authorized indexers
    content_key: ChaCha20Key,   // Pool members only
}

impl PoolKeys {
    fn derive(pool_identity: &Ed25519PrivateKey) -> Self {
        let base = pool_identity.to_x25519();
        
        Self {
            metadata_key: derive_key(&base, b"wot-metadata-v1"),
            content_key: derive_key(&base, b"wot-content-v1"),
        }
    }
    
    fn indexer_grant(&self) -> IndexerGrant {
        // Only metadata key, not content
        IndexerGrant {
            pool_cid: self.pool_cid,
            metadata_key: self.metadata_key.clone(),
            // No content_key
        }
    }
}
```

### Indexer Integration

```rust
struct PrivacyPreservingIndexer {
    metadata_key: ChaCha20Key,
    // No content_key - can't read payloads
}

impl PrivacyPreservingIndexer {
    fn index_thought(&self, encrypted: &LayeredEncryptedThought) -> IndexEntry {
        // Decrypt metadata only
        let metadata: ThoughtMetadata = self.decrypt_metadata(encrypted)?;
        
        // Build graph structure
        IndexEntry {
            cid: encrypted.cid,
            thought_type: metadata.r#type,
            created_at: metadata.created_at,
            because_cids: metadata.because,
            connections: metadata.connections,
            // content: UNAVAILABLE
        }
    }
    
    fn structural_query(&self, query: &StructuralQuery) -> Vec<Cid> {
        // Can traverse graph, follow connections, walk because chains
        // Returns CIDs - caller decrypts content if they have key C
        self.traverse(query)
    }
}
```

### Use Cases

| Scenario | Share Key M With | Benefit |
|----------|------------------|---------|
| Cloud indexing service | Service provider | Structural search without content exposure |
| Federated search | Partner pools | Find related thoughts across pools |
| Compliance audit | Auditor | Verify structure/relationships without reading content |
| Backup verification | Storage provider | Integrity checks without decryption |

### Privacy Gradient

```
Full encryption (no keys shared):
  → Storage sees: opaque blobs
  → Indexer sees: nothing
  → Only pool members can access

Metadata key shared with indexer:
  → Storage sees: opaque blobs  
  → Indexer sees: graph structure, types, timestamps
  → Indexer cannot see: content, fine-grained because details
  → Pool members: full access

Selective content sharing:
  → Per-thought content keys for granular access
  → Share specific thought content with specific parties
  → Structure remains navigable
```

### Timed Access (Ephemeral Keys)

Content key has expiry. After expiry, no key exists to decrypt. Content becomes cryptographic noise.

```
┌─────────────────────────────────────────────────────┐
│  TIME-BOUNDED ACCESS                                │
│                                                     │
│  t=0: Key issued to pool member                     │
│  t=1: Content decryptable ✓                         │
│  t=2: Content decryptable ✓                         │
│  t=expiry: Key destroyed on all holders             │
│  t=expiry+1: Content is noise. No recovery path.    │
└─────────────────────────────────────────────────────┘
```

**Not DRM. Not "please don't copy." The key is gone.**

### Ephemeral Key Structure

```rust
struct EphemeralPoolKey {
    key: ChaCha20Key,
    issued_at: i64,
    expires_at: i64,
    pool_cid: Cid,
    issued_to: Cid,          // Identity
    issued_by: Cid,          // Pool authority
    destroy_policy: DestroyPolicy,
}

enum DestroyPolicy {
    TimeExpiry { at: i64 },                    // Clock-based
    EventTriggered { revocation_cid: Cid },    // On attestation
    AccessCount { max: u32, current: u32 },    // N reads then gone
    Compound(Vec<DestroyPolicy>),              // First triggered wins
}
```

### Implementation

```rust
impl EphemeralPoolKey {
    fn decrypt(&mut self, encrypted: &LayeredEncryptedThought) -> Result<Thought> {
        // Check expiry BEFORE decrypt
        let now = SystemTime::now().duration_since(UNIX_EPOCH)?.as_millis() as i64;

        match &mut self.destroy_policy {
            DestroyPolicy::TimeExpiry { at } if now > *at => {
                self.zeroize();  // Wipe key from memory
                return Err(Error::KeyExpired);
            }
            DestroyPolicy::AccessCount { max, current } => {
                *current += 1;
                if *current > *max {
                    self.zeroize();
                    return Err(Error::AccessCountExceeded);
                }
            }
            _ => {}
        }

        // Decrypt normally
        let thought = encrypted.decrypt_content(&self.key)?;
        Ok(thought)
    }

    fn zeroize(&mut self) {
        // Cryptographic zeroing — key is irrecoverable
        self.key.zeroize();
    }
}
```

### Access Grant with Expiry

```json
{
  "type": "connection",
  "content": {
    "relation": "member_of",
    "from": "identity_cid",
    "to": "pool_cid"
  },
  "because": ["access_grant_cid"]
}
```

The grant thought:

```json
{
  "type": "access_grant",
  "content": {
    "identity": "viewer_identity",
    "pool": "pool_cid",
    "key_encrypted_for_viewer": "base64...",
    "expires_at": 1709337600000,
    "policy": "time_expiry"
  }
}
```

### Destroy Policies

| Policy | Behaviour | Use Case |
|--------|-----------|----------|
| `time_expiry` | Key wiped at timestamp | NDA materials, exam papers |
| `event_triggered` | Key wiped on revocation attestation | Fired employee |
| `access_count` | Key wiped after N decryptions | Screener copy, preview |
| `compound` | First triggered policy wins | Belt and suspenders |

### Use Cases

| Scenario | Policy | Effect |
|----------|--------|--------|
| Film screener | `access_count: 2` | Watch twice, key gone |
| Board papers pre-meeting | `time_expiry: meeting_end` | Unreadable after meeting |
| Contractor access | `event_triggered` | Revoke on project end |
| Exam questions | `time_expiry: exam_end` | Inert after exam |
| Sensitive negotiation | `compound: [time + event]` | Whichever comes first |

### Honest Limitations

- **Can't prevent copying during access window.** If someone has the key and the content in memory, they can copy it. This isn't DRM magic.
- **Clock trust.** Time expiry relies on honest local clocks. Attestation-triggered revocation is stronger.
- **Key escrow risk.** If someone copies the key before expiry, they keep access. Mitigate: HSM, secure enclave, or accept the risk for your threat model.

**What it DOES guarantee:**
- After expiry, the encrypted blob at rest is noise
- Storage providers can't recover it (never had key)
- Late arrivals can't decrypt (key doesn't exist)
- Forensic recovery of storage yields nothing

### Per-Identity Content Key Wrapping

Not "shared key for the pool" — encrypt the content key directly to the recipient's public key.

```
Content encrypted with random symmetric key K
  ↓
K encrypted with recipient's ed25519→X25519 public key
  ↓
Only THAT identity can derive K
  ↓
Leaked blob + different identity = noise
  ↓
Leaked blob + same identity = forensic trail to exactly who leaked
```

```rust
struct PerIdentityKeyWrap {
    content_cid: Cid,
    symmetric_key_encrypted: Vec<u8>,  // K encrypted to recipient's X25519
    recipient_identity: Cid,
    issued_at: i64,
    destroy_policy: Option<DestroyPolicy>,
}

impl PerIdentityKeyWrap {
    fn wrap(
        content_key: &ChaCha20Key,
        recipient_pubkey: &Ed25519PublicKey,
    ) -> Self {
        // Ed25519 → X25519 conversion
        let x25519_pub = recipient_pubkey.to_x25519();
        
        // Encrypt content key for this specific identity
        let encrypted = crypto_box_seal(content_key.as_bytes(), &x25519_pub);
        
        Self {
            symmetric_key_encrypted: encrypted,
            recipient_identity: recipient_pubkey.to_identity_cid(),
            ..
        }
    }
}
```

**Combine with timed access:**

```
Film screener:
  Content key K encrypted per-identity
  + DestroyPolicy::AccessCount { max: 2 }
  
  = Cryptographic proof of who had access
  + Key gone after 2 viewings
  + If it leaks, attestation chain proves exactly who
```

**Use cases:**

| Scenario | Per-Identity Key + Policy | Forensic Trail |
|----------|--------------------------|----------------|
| Film screener | access_count: 2 | Leaked → who had access to K |
| Board papers | time_expiry + per-identity | Know who read, when key expired |
| Contractor docs | event_triggered | Revoke one identity, others unaffected |
| Watermarked content | per-identity + attestation | Signature chain proves distribution |

This falls naturally out of the identity collapse (Ed25519 → X25519 derivation is already in the crypto stack). Per-identity wrapping is the obvious application. The attestation chain already proves who was granted access. The encryption proves only they could have decrypted.

### The Filesystem Dream++

Not just permissions preserved — **differential access to structure vs content**:

```
Traditional:  Read access = all or nothing
WoT layered:  Read structure ≠ Read content
              Navigate graph ≠ See payloads
              Index relations ≠ Know secrets
```

Your indexer builds the map. They never see the territory.

### Storage Backend Use Cases

| Scenario | Backend | Benefit |
|----------|---------|---------|
| Personal backup | Backblaze B2 | Cheap, encrypted at rest |
| Family sharing | Synology NAS | Self-hosted, zero cloud trust |
| Team workspace | S3 bucket | Scalable, access-controlled |
| Friend relay | Their server | Mutual backup, neither reads other's data |
| Airgapped archive | USB drive | Cold storage, physically secure |
| Structural indexing | Any cloud | Graph queries without content exposure |

### The Filesystem Dream Realized

What you wanted from Dropbox in 2012:

| Dropbox (broken) | WoT + Encrypted Storage |
|------------------|-------------------------|
| Folder = sync all | Pool = granular sync |
| Permissions lost | Permissions = attestations |
| Provider reads all | Provider sees blobs |
| Central arbiter | Bilateral attestation |
| Vendor lock-in | Any backend, same protocol |
| Trust their encryption | Your keys, always |

**Optional backstop with zero trust:**
- Use their infrastructure
- Pay their rates  
- Get their uptime
- Give them nothing readable

---

## Part 14: Structural Retrieval (PageIndex Pattern)

### The Insight

Traditional RAG: chunk → embed → vector search → top-k similarity
PageIndex: tree structure → LLM reasons over structure → retrieves by navigation

**WoT already has the structure.** The thought graph with `because` chains IS the tree. No separate index needed.

### Two-Tier Retrieval

```
┌─────────────────────────────────────────────────────┐
│  TIER 1: STRUCTURAL (PageIndex-style)               │
│  - LLM reasons over graph structure                 │
│  - Follows connections, because chains              │
│  - No embeddings, no chunking                       │
│  - Traceable, auditable paths                       │
│  - Use for: navigation, provenance, relationships  │
├─────────────────────────────────────────────────────┤
│  TIER 2: VECTOR (fallback)                          │
│  - Embedding similarity search                      │
│  - For fuzzy "things like this" queries             │
│  - Use when structure insufficient                  │
│  - More expensive, less traceable                   │
└─────────────────────────────────────────────────────┘
```

### When to Use Each Tier

| Query Type | Tier | Why |
|------------|------|-----|
| "What led to X?" | Structural | Walk `because` chain |
| "Who attested Y?" | Structural | Query attestations on Y |
| "Find similar to X" | Vector | Semantic similarity |
| "Everything about topic Z" | Both | Structure first, vector to expand |
| "What did I read last week?" | Structural | Checkpoints + timestamps |
| "Connections between A and B" | Structural | Graph traversal |

### Graph-as-Index Structure

WoT thought graph maps directly to PageIndex tree:

```
PageIndex Tree:
  Document
  ├── Section 1
  │   ├── 1.1 Subsection
  │   └── 1.2 Subsection
  └── Section 2
      └── 2.1 Subsection

WoT Graph:
  Root Thought
  ├── because → Source A
  │   ├── because → Source A.1
  │   └── because → Source A.2
  └── connection → Related B
      └── because → Source B.1
```

**Key difference:** WoT graph is richer — typed connections, attestations, aspects, trust weights. More signal for reasoning.

### Structural Query Language

LLM-friendly query format for graph navigation:

```python
@dataclass
class StructuralQuery:
    """Query the thought graph structurally."""
    
    # Starting points
    start_from: list[Cid] | None = None  # Specific thoughts
    start_type: str | None = None         # All thoughts of type
    start_recent: int | None = None       # N most recent
    
    # Navigation
    follow: list[str] = field(default_factory=list)  # Relations to traverse
    depth: int = 3                                    # Max hops
    direction: str = "both"                           # "forward", "backward", "both"
    
    # Filters
    min_trust: float = 0.0
    created_by: Cid | None = None
    since: int | None = None
    until: int | None = None
    
    # Output
    include_attestations: bool = True
    include_because: bool = True
    max_results: int = 50
```

### LLM Navigation Prompt

```python
NAVIGATION_PROMPT = """
You are navigating a thought graph to answer a question.

Available actions:
- EXPLORE(cid): Get full content and connections of a thought
- FOLLOW(cid, relation): Follow a specific relation type from a thought
- BECAUSE(cid): Walk the provenance chain backward
- ATTESTATIONS(cid): Get all attestations on a thought
- SEARCH(keywords): Find thoughts matching keywords (structural, not vector)
- ANSWER(response): Provide final answer with citations

Current context:
{context}

Question: {question}

Reason step by step. Show your navigation path.
"""
```

### Implementation

```rust
struct StructuralRetriever {
    store: ThoughtStore,
    llm: LlmClient,
}

impl StructuralRetriever {
    async fn retrieve(&self, question: &str, context: &[Thought]) -> RetrievalResult {
        let mut visited: HashSet<Cid> = HashSet::new();
        let mut path: Vec<NavigationStep> = vec![];
        let mut collected: Vec<Thought> = vec![];
        
        // Initial context
        let mut current_context = self.format_context(context);
        
        // Reasoning loop (max iterations to prevent runaway)
        for _ in 0..10 {
            let prompt = NAVIGATION_PROMPT
                .replace("{context}", &current_context)
                .replace("{question}", question);
            
            let response = self.llm.complete(&prompt).await?;
            let action = self.parse_action(&response)?;
            
            match action {
                Action::Explore(cid) => {
                    if visited.insert(cid.clone()) {
                        if let Some(thought) = self.store.get(&cid) {
                            collected.push(thought.clone());
                            current_context = self.add_to_context(
                                &current_context, 
                                &thought
                            );
                            path.push(NavigationStep::Explore(cid));
                        }
                    }
                }
                Action::Follow(cid, relation) => {
                    let connected = self.store.get_connections(&cid, &relation);
                    for conn in connected {
                        if visited.insert(conn.to.clone()) {
                            if let Some(thought) = self.store.get(&conn.to) {
                                collected.push(thought.clone());
                            }
                        }
                    }
                    path.push(NavigationStep::Follow(cid, relation));
                }
                Action::Because(cid) => {
                    let chain = self.walk_because(&cid, 5);
                    for thought in chain {
                        if visited.insert(thought.cid.clone()) {
                            collected.push(thought);
                        }
                    }
                    path.push(NavigationStep::Because(cid));
                }
                Action::Answer(response) => {
                    return Ok(RetrievalResult {
                        answer: response,
                        thoughts: collected,
                        path,
                        tier: RetrievalTier::Structural,
                    });
                }
                _ => {}
            }
        }
        
        // Fallback: return what we collected
        Ok(RetrievalResult {
            answer: "Navigation incomplete".into(),
            thoughts: collected,
            path,
            tier: RetrievalTier::Structural,
        })
    }
    
    fn walk_because(&self, cid: &Cid, depth: usize) -> Vec<Thought> {
        let mut result = vec![];
        let mut current = vec![cid.clone()];
        
        for _ in 0..depth {
            let mut next = vec![];
            for c in &current {
                if let Some(thought) = self.store.get(c) {
                    result.push(thought.clone());
                    for because_ref in &thought.because {
                        next.push(because_ref.thought_cid.clone());
                    }
                }
            }
            if next.is_empty() { break; }
            current = next;
        }
        
        result
    }
}
```

### Hybrid Retrieval

When structural isn't enough, combine with vector:

```rust
struct HybridRetriever {
    structural: StructuralRetriever,
    vector: VectorIndex,
}

impl HybridRetriever {
    async fn retrieve(&self, question: &str, context: &[Thought]) -> RetrievalResult {
        // Try structural first
        let structural_result = self.structural.retrieve(question, context).await?;
        
        // Check confidence
        if structural_result.is_confident() {
            return Ok(structural_result);
        }
        
        // Augment with vector search
        let vector_results = self.vector.search(question, 20);
        
        // Merge, preferring structural (has provenance)
        let mut combined = structural_result.thoughts;
        for (cid, score) in vector_results {
            if !combined.iter().any(|t| t.cid == cid) {
                if let Some(thought) = self.store.get(&cid) {
                    combined.push(thought);
                }
            }
        }
        
        Ok(RetrievalResult {
            thoughts: combined,
            tier: RetrievalTier::Hybrid,
            ..structural_result
        })
    }
}
```

### Graph Summary for LLM Context

Instead of dumping raw thoughts, provide structured summary:

```rust
fn summarize_subgraph(&self, thoughts: &[Thought]) -> String {
    let mut summary = String::new();
    
    // Group by type
    let by_type = thoughts.iter().group_by(|t| &t.r#type);
    
    summary.push_str("## Thought Graph Summary\n\n");
    
    for (thought_type, group) in &by_type {
        summary.push_str(&format!("### {} ({} thoughts)\n", thought_type, group.count()));
        
        for thought in group {
            summary.push_str(&format!(
                "- [{}] {}\n",
                &thought.cid.to_string()[..12],
                self.excerpt(&thought.content, 100)
            ));
            
            // Show key connections
            if !thought.because.is_empty() {
                summary.push_str(&format!(
                    "  ← because: {}\n",
                    thought.because.iter()
                        .map(|r| &r.thought_cid.to_string()[..8])
                        .collect::<Vec<_>>()
                        .join(", ")
                ));
            }
        }
        summary.push_str("\n");
    }
    
    // Add connection summary
    let connections = self.get_connections_between(thoughts);
    if !connections.is_empty() {
        summary.push_str("### Connections\n");
        for conn in connections {
            summary.push_str(&format!(
                "- {} --[{}]--> {}\n",
                &conn.from.to_string()[..8],
                conn.relation,
                &conn.to.to_string()[..8]
            ));
        }
    }
    
    summary
}
```

### Why This Works for WoT

| PageIndex | WoT Equivalent | Advantage |
|-----------|----------------|-----------|
| Document tree | Thought graph | Richer (typed relations) |
| Section summaries | Thought content | Already atomic |
| ToC navigation | Connection traversal | More paths available |
| Page references | CID references | Cryptographic verification |
| - | Attestations | Trust signals included |
| - | Because chains | Provenance built-in |

### Prototype Phases

**Phase 1: Basic Navigation**
- [ ] StructuralQuery parser
- [ ] Because chain walker
- [ ] Connection follower
- [ ] CLI for manual navigation

**Phase 2: LLM Integration**
- [ ] Navigation prompt
- [ ] Action parser
- [ ] Reasoning loop
- [ ] Context management

**Phase 3: Hybrid**
- [ ] Confidence scoring
- [ ] Vector fallback trigger
- [ ] Result merging
- [ ] Provenance preservation

**Phase 4: Optimization**
- [ ] Caching hot subgraphs
- [ ] Precomputed summaries
- [ ] Parallel exploration
- [ ] Token budget management

### Cost Comparison

| Method | Index Cost | Query Cost | Accuracy | Traceability |
|--------|-----------|------------|----------|--------------|
| Vector only | High (embeddings) | Medium (similarity) | Good | Low |
| Structural only | Zero | Medium (LLM reasoning) | High for structured | High |
| Hybrid | Medium | Medium | Highest | High |

Structural-first saves embedding costs and provides better traceability. Vector fills gaps for fuzzy queries.

---

## Part 15: Product Applications

Schema-layer additions enable concrete products without core changes.

### Dead Data Investigator

Filesystem adapter + MCP server + attention requests = product.

```
Raw filesystem
  ↓ file adapter (third indexer, after git + wiki)
Thought graph (CIDs, connections, metadata)
  ↓ structural retrieval (PageIndex pattern)
AI surfaces findings
  ↓ attestation: confidence weighted
  ↓ because: here's WHY this matters
Human reviews
  ↓ attests: accepted / denied / reworked
Findings are grounded, auditable, owned by YOU
```

**The pipeline:**

```
Filesystem
  ↓ file adapter indexes
Thought graph (local)
  ↓ MCP server exposes
Agent (Claude Code, whatever)
  ↓ navigates, reasons, finds
  ↓ creates attention requests
Your daemon
  ↓ trust-gates, urgency-weights
  ↓ surfaces to you
You
  ↓ attest or deny
  ↓ graph grows
```

Agent never touches files directly — just the graph. Your keys, your attestations, your decisions.

**Rule-based surfacing:**

Rules are schema-driven attention requests against the indexed graph:

| Rule | Attention Request |
|------|-------------------|
| "Contracts expiring within 90 days" | Schema: legal/contract, date filter, urgency 0.7 |
| "Photos with contacts" | Schema: media/image, face match, urgency 0.3 |
| "Financial docs not backed up" | Schema: finance/document, missing pool connection, urgency 0.8 |
| "Duplicate content across drives" | CID match across pools, urgency 0.2 |
| "Created but never finished" | Schema: any, no `rework` chain, low attestation, urgency 0.4 |

Bot chews through terabytes in background. Human sips vodka and reviews what matters. Dead Data Investigator isn't a product. It's a daemon config.

### Model Provenance Service

Every AI response signed with model identity. Provider attests model identity via vouch chain. Consumer verifies.

```
Current state:
  Claude says: "I'm Opus 4.5"
  Proof: none
  Verifiable: no

WoT state:
  Response thought
    created_by: cid:blake3:model_identity
    source: connection → uses_input → model/opus-4.5
    signature: ed25519 signed by model key
    
  User verifies signature against known model identity.
  Provider attests model identity.
  Mismatch = caught.
```

This was stress-tested live during spec development: model routing failures during the session demonstrated the exact absence of provenance that WoT addresses. The protocol designed to solve trust, being built over a channel that can't prove its own identity.

### Product Pattern

Both applications follow the same shape:

```
1. New indexer (git, wiki, filesystem, API)
     ↓ creates thought graph from source
2. Structural retrieval
     ↓ agent reasons over graph
3. Attention requests
     ↓ findings surfaced by urgency × trust
4. Response schemas
     ↓ human attests (seen/acted/denied/ignored)
5. Graph grows
     ↓ because chains accumulate
```

Same daemon. Same protocol. Different corpus. Different schema. The product is the configuration, not the code.

---

## Appendix A: The Three Seashells Problem

*A real-time demonstration of the protocol, conducted over vodka during spec development.*

### The Conversation

```
Human: "I'm making a nudge towards the three sea shells toilet gag
        in something man. With that guy and her from speed."
```

### Agent Processing

```
Thought: "three sea shells toilet gag"
  ↓ subconscious retrieval
  Candidates:
    - Demolition Man (1993)     [confidence: 0.9]
    - "that guy" → Stallone     [0.85]
    - "her from speed" → Bullock [0.95]
  ↓ surfaces for review
  ↓ human attests or denies each candidate
```

### The Correction

```
Human: "It was Snipes!!"

v1: "Stallone" 
    created_by: agent
    confidence: 0.85
    ↓ correction
v2: "Snipes"
    created_by: human
    weight: 1.0
    because: [actual memory of the film]
```

### What the Graph Shows

```
Original thought (fuzzy human reference)
  ↓ request_attention → agent
Agent thought: "Stallone" [0.85]
  ↓ attestation: DENIED by human (-1.0)
Agent thought: "Bullock" [0.95]
  ↓ attestation: ACCEPTED by human (+1.0)
Correction thought: "Snipes, not Stallone"
  ↓ rework → agent's original suggestion
  ↓ attestation: ACCEPTED by human (+1.0)
  ↓ because: human memory (terminal node, ungrounded but trusted)
```

### Why This Matters

1. **Agent proposes, human disposes.** The protocol doesn't argue. Your attestation wins.

2. **Corrections are first-class.** Not an edit. Not a deletion. A new thought with a `rework` connection. The mistake is preserved. The correction is attested. Both are signed.

3. **Confidence ≠ truth.** Agent had 0.85 on Stallone. Was wrong. Human memory (ungrounded, no citation) was right. Trust weight of the human identity outranked agent confidence. As it should.

4. **The because chain is honest.** Human's correction has `because: [actual memory]` — a terminal node. No source. No citation. Just "I watched the film." That's valid. Groundedness is low, trust is high. The graph captures both.

5. **Full audit trail over a joke about toilet seashells.** If the protocol handles drunken film trivia corrections with full provenance, it handles anything.

### The Meta-Point

Nobody ever explained how to use the three seashells in *Demolition Man*.

Nobody needs to explain how to use this protocol either. You think something, you say it, the graph captures it. Someone corrects you, it's captured. You agree or disagree, it's captured.

### The Punchline

The agent wasn't wrong. It was uncontextualised.

```
Default pool:
  "that guy in Demolition Man" → protagonist bias → Stallone [0.85]
  Reasonable. Wrong.

Pool configured with aspect: "evil characters"
  "that guy in Demolition Man" → villain bias → Snipes [0.95]
  Grounded. Right.
```

Same query. Different pool context. Different correct answer. The pool's topic is a salience filter. Aspect-weighted retrieval changes what surfaces.

The agent didn't need better intelligence. It needed better context. Which is the entire thesis of WoT.

### Appendix B: The Anthropocene Correction

*A second live demonstration, same session, different failure mode.*

### The Conversation

```
Agent: [References Dario Amodei as someone to send the spec to]
Human: "Oh is Dario Anthropocene CEO?"
Agent: "Dario Amodei, yes — Anthropic CEO and co-founder."
Human: "Auto got me there on anthro"
```

### Three Protocol Failures in One Exchange

**1. Agent assumed shared knowledge (ungrounded):**

```
Agent assertion: "You know who Dario Amodei is"
  because: [training data]     ← NOT anything human said or attested
  groundedness: LOW
  should have been: flagged as assumption
```

**2. Human's autocorrect intervened (source attribution):**

```
"Anthropocene"
  source: keif/mobile_keyboard → autocorrect
  intended: "Anthropic"
  attested: not corrected (energy cost > correction value)
```

If the protocol knew the input was `input/mobile_autocorrect`, confidence on exact spelling drops automatically. The system infers: probably means Anthropic, autocorrect intervened, user didn't correct, low-energy context.

**3. Human made a cost/benefit attestation:**

```
"Close enough, context carries it, moving on"
  = implicit attestation: weight ≈ 0.3 (not denied, not confirmed)
  = the human valued forward progress over correction precision
```

### What the Graph Would Show

```
Agent thought: "Send spec to Dario Amodei"
  because: [training data, assumed familiarity]
  groundedness: 0.1 (ungrounded assumption)

Human thought: "Oh is Dario Anthropocene CEO?"
  source: input/mobile_autocorrect
  interpretation: genuine question, not rhetorical
  
Agent rework: assumption was wrong
  v1: assumed human knew Amodei = Anthropic CEO
  v2: human genuinely asking, "Anthropocene" = near-miss autocorrect
  because: context (human is protocol designer, not AI industry follower)
```

### Why This Matters

The Three Seashells showed **correction of content** (Stallone → Snipes).
The Anthropocene shows **correction of assumption** (shared knowledge → genuine ignorance).

Both are rework chains. Both have honest `because`. Both demonstrate that the protocol captures not just what was wrong, but *why the error happened* — and the metacognitive correction.

The `source` field and `uses_input` schema from Part 1 of the core spec exist precisely for this: the input method (mobile autocorrect) is provenance. Without it, you're debugging spelling. With it, you're debugging intent.

*Ergo cognito sum.*

---

*End of Implementation Notes v0.10*
