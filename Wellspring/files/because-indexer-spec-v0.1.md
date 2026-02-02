# Because Indexer Specification v0.1

## Purpose

The Because Indexer transforms existing content repositories into Web of Thought (WoT) format, creating a corpus of thoughts with cryptographic addressing and provenance chains. This enables:

1. Testing WoT query and retrieval systems against real data
2. Bootstrapping the daemon's context injection with meaningful content
3. Validating the thought/because-chain model against existing knowledge structures
4. Creating seed libraries for new WoT users

## Background: WoT Core Concepts (v0.8)

### Thought

The atomic unit of WoT. Every thought has:

```json
{
  "cid": "cid:blake3:...",           // Content-addressed ID (BLAKE3 hash)
  "type": "basic",                    // Schema type
  "content": "string or object",      // The payload
  "created_by": "cid:blake3:...",     // Identity CID (required, never null)
  "created_at": 1769863335534,        // Unix timestamp in milliseconds
  "because": ["cid:...", ...],        // What led to this thought
  "signature": "hex...",              // Ed25519 signature proving creator
  "source": "keif/desktop_keyboard"   // Input attribution: WHO/HOW
}
```

**Properties**:
- **Immutable**: once created, content never changes
- **Content-addressed**: CID = BLAKE3 hash of (content + created_by + because)
- **Always attributed**: `created_by` is required, never null
- **Signed**: signature proves creator authenticity
- **Grounded**: `because` links to the thoughts that led here
- **Source-tracked**: `source` records input method (keyboard, voice, bot, etc.)

**Note (v0.8):** There is no `visibility` field. Access is determined by the connection graph — what pools a thought is connected to determines where it syncs and who can see it.

### Access Model (v0.8)

Access = Traversability. For indexed content:

1. Indexer creates thoughts from source (git commits, wiki pages, etc.)
2. Indexer creates connection thoughts: `thought → published_to → index_pool`
3. Access to indexed content = membership in the index pool

```
INDEXED THOUGHT
    ↓
CONNECTION: thought → published_to → index_pool
    ↓
Who can traverse to index_pool? → They can see the thought
```

### CID Format

WoT uses BLAKE3 (preferred) or SHA-256:

```
cid:blake3:5cecc66b61e356cef45f35f5e3da679e8d335d7e224c08cddd2f3b7c680e4393
cid:sha256:099688fae3f45a8dd01fb13423bba8d8f901b851134adbeb557b357b6a475104
```

For development traces, shorter IDs are acceptable:
```
trace:c891983b97655d16
```

### Because Chain

The provenance trail. "Why does this thought exist?"
- A commit exists BECAUSE of its parent commit
- A wiki edit exists BECAUSE of the previous version + the sources it cites
- An answer exists BECAUSE of the question asked
- Empty `because` = ungrounded assertion (terminal node)

Walk `because` backward and you traverse the reasoning path.

### Rework Chain (v0.8)

Edit history is separate from `because`. "How did this thought become this?"

The rework chain is formed by **connection thoughts** with `relation: rework`:

```json
{
  "type": "connection",
  "content": {
    "relation": "rework",
    "from": "current_version_cid",
    "to": "previous_version_cid"
  }
}
```

Not a new primitive — just connection thoughts linking versions together.

### Input Source Attribution

The `source` field tracks WHO said what and HOW:

```
keif/desktop_keyboard       — human typing
keif/verbally_transcribed   — voice-to-text
agent-model/autocorrect     — model intervention
chat/user                   — user in chat interface
chat/assistant              — AI response
git/wot-technology          — indexed from git repo
wiki/wikipedia              — indexed from wiki
```

This enables training data with consent: every keystroke-to-final journey becomes supervised learning data.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BECAUSE INDEXER                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ Git Adapter │    │Wiki Adapter │    │Site Adapter │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            ▼                                │
│                   ┌─────────────────┐                       │
│                   │  Transform Core │                       │
│                   │  - CID compute  │                       │
│                   │  - Chain build  │                       │
│                   │  - Type infer   │                       │
│                   └────────┬────────┘                       │
│                            │                                │
│                            ▼                                │
│                   ┌─────────────────┐                       │
│                   │  Thought Store  │                       │
│                   │  - SQLite/PG    │                       │
│                   │  - Merkle DAG   │                       │
│                   └────────┬────────┘                       │
│                            │                                │
│                            ▼                                │
│                   ┌─────────────────┐                       │
│                   │   Index Layer   │                       │
│                   │  - Full text    │                       │
│                   │  - Vector embed │                       │
│                   │  - Graph query  │                       │
│                   └────────┬────────┘                       │
│                            │                                │
│                            ▼                                │
│                   ┌─────────────────┐                       │
│                   │  Query API/CLI  │                       │
│                   │  - Search       │                       │
│                   │  - Walk chains  │                       │
│                   │  - MCP server   │                       │
│                   └─────────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Phase 1: Git Adapter

Git is the ideal first source — it already has content addressing and parent chains.

### Why Git First

| Git Concept | WoT Mapping | Notes |
|-------------|-------------|-------|
| Commit SHA | CID | Already content-addressed |
| Parent commit | because | Direct mapping |
| Commit message | thought.content | Primary content |
| Diff | rework material | Shows what changed |
| Author + email | identity | Needs identity mapping |
| Branch | pool | Logical grouping |
| Tag | attestation | "This commit is significant" |

### Git Adapter Interface

```rust
pub struct GitAdapter {
    repo_path: PathBuf,
    identity_map: HashMap<String, IdentityCid>,  // email -> WoT identity
}

impl GitAdapter {
    /// Walk all commits, oldest first
    fn walk_commits(&self) -> impl Iterator<Item = GitCommit>;
    
    /// Transform a git commit into a WoT thought
    fn commit_to_thought(&self, commit: GitCommit) -> Thought;
    
    /// Extract file changes as child thoughts
    fn diff_to_thoughts(&self, commit: GitCommit) -> Vec<Thought>;
}
```

### Commit → Thought Transform

```rust
fn commit_to_thought(&self, commit: GitCommit) -> Thought {
    let content = format!(
        "{}\n\n---\nFiles: {}\nAdditions: {}\nDeletions: {}",
        commit.message,
        commit.files_changed,
        commit.additions,
        commit.deletions
    );
    
    let created_by = self.identity_map.get(&commit.author_email)
        .cloned()
        .unwrap_or_else(|| create_anonymous_identity(&commit.author_email));
    let because: Vec<String> = commit.parents.iter()
        .map(|p| self.commit_sha_to_cid(p))
        .collect();
    
    // CID = blake3(content + created_by + because)
    let cid = compute_cid(&content, &created_by, &because);
    
    Thought {
        cid,
        r#type: "git/commit".into(),
        content,
        created_by,
        created_at: commit.timestamp.timestamp_millis(),  // ms since epoch
        because,
        signature: sign(&cid, &self.indexer_privkey),
        source: format!("git/{}", self.repo_name),
    }
    // Note: No visibility field. Access controlled via connection to index pool.
}
```

**Output JSON (v0.8 — no visibility):**

```json
{
  "cid": "cid:blake3:abc123...",
  "type": "git/commit",
  "content": "feat: Add because indexer\n\n---\nFiles: 5\nAdditions: 342\nDeletions: 12",
  "created_by": "cid:blake3:author123...",
  "created_at": 1769863335534,
  "because": ["cid:blake3:parent456..."],
  "signature": "ed25519:...",
  "source": "git/wot-technology"
}
```

**Plus connection thought for pool publication:**

```json
{
  "cid": "cid:blake3:conn...",
  "type": "connection",
  "content": {
    "from": "cid:blake3:abc123...",
    "to": "cid:blake3:index_pool...",
    "relation": "published_to"
  },
  "created_by": "cid:blake3:indexer...",
  "created_at": 1769863335600,
  "because": ["cid:blake3:abc123..."],
  "signature": "...",
  "source": "indexer/publish"
}
```

### File Diff → Thought Transform

Each file change in a commit can become a child thought:

```rust
fn diff_to_thoughts(&self, commit: GitCommit) -> Vec<Thought> {
    commit.diffs.iter().map(|diff| {
        let content = format!(
            "File: {}\n\n```\n{}\n```",
            diff.path,
            diff.patch
        );
        
        Thought {
            cid: compute_cid(&content),
            content,
            author: /* same as commit */,
            created: commit.timestamp,
            because: vec![
                self.commit_sha_to_cid(&commit.sha),  // because of this commit
                self.get_previous_file_cid(&diff.path, &commit),  // because of previous version
            ],
            rework: self.get_file_rework_chain(&diff.path, &commit),
            pool: self.branch_to_pool(&commit.branch),
            thought_type: Some("git/file-change".into()),
        }
    }).collect()
}
```

### Identity Handling

Git has email addresses. WoT has cryptographic identities. Options:

1. **Anonymous mapping**: Create pseudo-identities from email hashes
2. **Manual mapping**: Config file mapping email → real WoT identity
3. **Discovery**: If WoT identity published at email domain, resolve it

For corpus testing, anonymous mapping is sufficient:

```rust
fn create_anonymous_identity(email: &str) -> IdentityCid {
    let pseudo_content = format!("anonymous:git:{}", email);
    compute_cid(&pseudo_content)
}
```

### CLI Usage

```bash
# Index a local repo
wot-index git ./my-repo --branch main --output ./thoughts.db

# Index with identity mapping
wot-index git ./my-repo --identity-map ./identities.json

# Index remote repo
wot-index git https://github.com/user/repo --shallow-since 2024-01-01

# Index multiple repos into shared pool
wot-index git ./repo1 ./repo2 --pool "my-projects"
```

## Phase 2: Wiki Adapter

Wikis have different structure: pages with revision history and internal links.

### Wiki Sources

| Source | API/Method | Notes |
|--------|------------|-------|
| MediaWiki | API + dumps | Wikipedia, etc |
| GitHub Wiki | Git clone | It's just a git repo |
| Notion | API | Needs auth |
| Obsidian | Local files | Markdown + [[links]] |
| Roam | JSON export | Block-based |

### Page Version → Thought Transform

```rust
fn page_version_to_thought(&self, page: WikiPage, version: PageVersion) -> Thought {
    Thought {
        cid: compute_cid(&version.content),
        content: version.content,
        author: self.user_to_identity(&version.editor),
        created: version.timestamp,
        because: vec![
            // Links to other pages = semantic because
            self.extract_wiki_links(&version.content),
            // Previous version = temporal because
            version.previous.map(|p| self.version_to_cid(&p)),
            // Categories = pool membership signals
        ].into_iter().flatten().collect(),
        rework: self.get_page_history(&page.title)
            .iter()
            .take_while(|v| v.id != version.id)
            .map(|v| self.version_to_cid(v))
            .collect(),
        pool: self.category_to_pool(&page.categories),
        thought_type: Some("wiki/page".into()),
    }
}
```

### Link Extraction

Wiki links are candidate because relationships:

```rust
fn extract_wiki_links(&self, content: &str) -> Vec<Cid> {
    // [[Page Name]] → lookup page CID
    // [text](url) → lookup or create URL thought
    // Citations → high-confidence because
    
    let mut because = vec![];
    
    // Internal wiki links
    for link in WIKI_LINK_REGEX.find_iter(content) {
        if let Some(page_cid) = self.page_title_to_cid(&link) {
            because.push(page_cid);
        }
    }
    
    // External citations (higher weight)
    for citation in CITATION_REGEX.find_iter(content) {
        let url_thought = self.url_to_thought(&citation);
        because.push(url_thought.cid);
    }
    
    because
}
```

## Phase 3: Sitemap Adapter

Simplest source — just URL hierarchy.

```rust
fn sitemap_to_thoughts(&self, sitemap_url: &str) -> Vec<Thought> {
    let sitemap = fetch_and_parse_sitemap(sitemap_url);
    
    sitemap.urls.iter().map(|url| {
        let content = fetch_page_content(url);
        let parent_url = get_parent_url(url);  // /foo/bar → /foo
        
        Thought {
            cid: compute_cid(&content),
            content,
            author: self.site_to_identity(sitemap_url),
            created: url.lastmod.unwrap_or_else(Utc::now),
            because: vec![
                parent_url.map(|p| self.url_to_cid(&p)),
                self.extract_links(&content),
            ].into_iter().flatten().collect(),
            rework: vec![],  // No history from sitemaps
            pool: self.site_to_pool(sitemap_url),
            thought_type: Some("web/page".into()),
        }
    }).collect()
}
```

## Phase 4: Transform Core

Shared logic across all adapters.

### CID Computation (BLAKE3 preferred)

```rust
use blake3::Hasher;

/// Compute CID per v0.7 spec: hash(content + created_by + because)
fn compute_cid(content: &str, created_by: &str, because: &[String]) -> String {
    let mut hasher = Hasher::new();
    
    // Hash content
    hasher.update(content.as_bytes());
    
    // Hash created_by
    hasher.update(created_by.as_bytes());
    
    // Hash because chain (order matters)
    for b in because {
        hasher.update(b.as_bytes());
    }
    
    let hash = hasher.finalize();
    format!("cid:blake3:{}", hex::encode(hash.as_bytes()))
}

// For compatibility with existing SHA-256 content
fn compute_cid_sha256(content: &str, created_by: &str, because: &[String]) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    hasher.update(created_by.as_bytes());
    for b in because {
        hasher.update(b.as_bytes());
    }
    let hash = hasher.finalize();
    format!("cid:sha256:{}", hex::encode(hash))
}
```

### Thought Validation

```rust
fn validate_thought(thought: &Thought) -> Result<(), ValidationError> {
    // CID must match content
    let computed = compute_cid(&thought.content);
    if computed != thought.cid {
        return Err(ValidationError::CidMismatch);
    }
    
    // Because references must exist (or be marked external)
    for because_cid in &thought.because {
        if !store.exists(because_cid) && !is_external_ref(because_cid) {
            return Err(ValidationError::MissingBecause(because_cid.clone()));
        }
    }
    
    // Rework chain must be consistent
    for rework_cid in &thought.rework {
        if !store.exists(rework_cid) {
            return Err(ValidationError::MissingRework(rework_cid.clone()));
        }
    }
    
    Ok(())
}
```

### Type Inference

When source doesn't provide explicit type:

```rust
fn infer_thought_type(content: &str, source_hint: &str) -> Option<String> {
    // Code detection
    if looks_like_code(content) {
        return Some(format!("code/{}", detect_language(content)));
    }
    
    // Question detection
    if content.trim().ends_with('?') || content.starts_with("How ") {
        return Some("query/question".into());
    }
    
    // List detection
    if content.lines().filter(|l| l.starts_with("- ")).count() > 3 {
        return Some("structure/list".into());
    }
    
    // Default to source hint
    Some(source_hint.into())
}
```

## Phase 5: Storage Layer

### SQLite Schema (aligned with v0.8)

```sql
-- Core thought storage (matches JSONL format, no visibility field)
CREATE TABLE thoughts (
    cid TEXT PRIMARY KEY,              -- "cid:blake3:..." or "cid:sha256:..."
    type TEXT NOT NULL,                -- "basic", "git/commit", "wiki/page", etc.
    content TEXT NOT NULL,             -- JSON-encoded (string or object)
    created_by TEXT NOT NULL,          -- Identity CID (required)
    created_at INTEGER NOT NULL,       -- Unix timestamp in milliseconds
    signature TEXT NOT NULL,           -- Ed25519 hex signature
    source TEXT                        -- Input attribution: "git/repo", "wiki/name"
);

-- Because links (separate table for efficient traversal)
CREATE TABLE because_links (
    thought_cid TEXT NOT NULL,
    because_cid TEXT NOT NULL,
    position INTEGER NOT NULL,         -- Order matters for some chains
    PRIMARY KEY (thought_cid, because_cid),
    FOREIGN KEY (thought_cid) REFERENCES thoughts(cid)
);

-- Connections (v0.8: how thoughts relate, including pool publication)
CREATE TABLE connections (
    cid TEXT PRIMARY KEY,              -- Connection thought's CID
    from_cid TEXT NOT NULL,            -- Source thought
    to_cid TEXT NOT NULL,              -- Target thought (or pool)
    relation TEXT NOT NULL,            -- "published_to", "rework", "supports", etc.
    FOREIGN KEY (cid) REFERENCES thoughts(cid)
);

-- Identities (anonymous mapping for indexed sources)
CREATE TABLE identities (
    cid TEXT PRIMARY KEY,
    identity_type TEXT NOT NULL,       -- 'anonymous', 'mapped', 'verified'
    source_id TEXT,                    -- email, username, etc.
    display_name TEXT,
    public_key TEXT                    -- Ed25519 pubkey if verified
);

-- Pools (for managing index access)
CREATE TABLE pools (
    cid TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    admin_cid TEXT NOT NULL,
    FOREIGN KEY (cid) REFERENCES thoughts(cid)
);

-- Indexes for common queries
CREATE INDEX idx_thoughts_type ON thoughts(type);
CREATE INDEX idx_thoughts_created_by ON thoughts(created_by);
CREATE INDEX idx_thoughts_created_at ON thoughts(created_at);
CREATE INDEX idx_thoughts_source ON thoughts(source);
CREATE INDEX idx_because_target ON because_links(because_cid);
CREATE INDEX idx_connections_from ON connections(from_cid);
CREATE INDEX idx_connections_to ON connections(to_cid);
CREATE INDEX idx_connections_relation ON connections(relation);

-- Full-text search (SQLite FTS5)
CREATE VIRTUAL TABLE thoughts_fts USING fts5(
    content,
    cid UNINDEXED,
    tokenize='porter unicode61'
);
```

**JSONL Export Format (v0.8 — no visibility field):**

```jsonl
{"cid":"cid:blake3:...","type":"git/commit","content":"...","created_by":"cid:blake3:...","created_at":1769863335534,"because":["cid:blake3:..."],"signature":"...","source":"git/wot-technology"}
```

**Connection thought (controls access via pool publication):**

```jsonl
{"cid":"cid:blake3:conn...","type":"connection","content":{"from":"cid:blake3:thought...","to":"cid:blake3:pool...","relation":"published_to"},"created_by":"cid:blake3:indexer...","created_at":1769863335600,"because":["cid:blake3:thought..."],"signature":"...","source":"indexer/auto"}
```

## Phase 6: Index Layer

### Vector Embeddings (Semantic Search)

Integration with CocoIndex or direct embedding:

```rust
struct VectorIndex {
    model: SentenceTransformer,
    index: HnswIndex,
}

impl VectorIndex {
    fn index_thought(&mut self, thought: &Thought) {
        let embedding = self.model.encode(&thought.content);
        self.index.insert(thought.cid.clone(), embedding);
    }
    
    fn search(&self, query: &str, top_k: usize) -> Vec<(Cid, f32)> {
        let query_embedding = self.model.encode(query);
        self.index.search(&query_embedding, top_k)
    }
}
```

### Graph Traversal

```rust
struct GraphIndex {
    store: ThoughtStore,
}

impl GraphIndex {
    /// Walk because chain backwards (why does this exist?)
    fn walk_because(&self, cid: &Cid, max_depth: usize) -> BecauseTree {
        self.walk_recursive(cid, max_depth, Direction::Because)
    }
    
    /// Walk forward (what was built on this?)
    fn walk_dependents(&self, cid: &Cid, max_depth: usize) -> DependentTree {
        // Find all thoughts where this CID is in their because[]
        self.walk_recursive(cid, max_depth, Direction::Dependent)
    }
    
    /// Walk rework chain (how did this evolve?)
    fn walk_rework(&self, cid: &Cid) -> Vec<Thought> {
        let thought = self.store.get(cid)?;
        let mut chain = vec![thought.clone()];
        
        for rework_cid in &thought.rework {
            if let Some(prev) = self.store.get(rework_cid) {
                chain.push(prev);
            }
        }
        
        chain
    }
}
```

## Phase 7: Query API

### CLI Interface

```bash
# Search thoughts
wot search "pricing intelligence" --limit 10

# Get thought with because chain
wot get <cid> --chain

# Walk from a thought
wot walk <cid> --direction because --depth 3

# Export subgraph
wot export <cid> --format json --include-chain

# Stats
wot stats --pool <pool_cid>
```

### REST API

```
GET /thoughts/<cid>
GET /thoughts/<cid>/because
GET /thoughts/<cid>/dependents
GET /search?q=<query>&limit=<n>
POST /thoughts  (for adding new thoughts)
```

### MCP Server (LLM Context Injection)

The primary use case: daemon needs to FIND relevant thoughts to inject into LLM context before API calls.

```rust
struct WotMcpServer {
    store: ThoughtStore,
    vector_index: VectorIndex,
    graph: GraphIndex,
}

impl McpServer for WotMcpServer {
    fn list_tools(&self) -> Vec<Tool> {
        vec![
            Tool::new("search_thoughts", "Semantic search over thought corpus"),
            Tool::new("get_thought", "Get a specific thought by CID"),
            Tool::new("walk_because", "Walk the because chain backwards"),
            Tool::new("walk_dependents", "Find thoughts that cite this one"),
            Tool::new("find_by_type", "Find thoughts by type (git/commit, wiki/page, etc)"),
            Tool::new("recent_thoughts", "Get recently created/accessed thoughts"),
        ]
    }
    
    fn call_tool(&self, name: &str, args: Value) -> Value {
        match name {
            "search_thoughts" => {
                let query = args["query"].as_str().unwrap();
                let limit = args.get("limit").and_then(|v| v.as_u64()).unwrap_or(25);
                
                let results = self.vector_index.search(query, limit as usize);
                
                // Format for LLM context injection (CID-referenced graph)
                self.format_as_thought_graph(results)
            }
            "walk_because" => {
                let cid = args["cid"].as_str().unwrap();
                let depth = args.get("depth").and_then(|v| v.as_u64()).unwrap_or(3);
                
                let chain = self.graph.walk_because(cid, depth as usize);
                self.format_chain_for_context(chain)
            }
            // ...
        }
    }
}
```

**Context Injection Format** (thoughts as CID-referenced graph, not flattened prose):

```xml
<thought_context>
  <thought cid="cid:blake3:abc123">
    <type>git/commit</type>
    <content>feat: Add because indexer</content>
    <because>cid:blake3:parent456</because>
    <source>git/wot-technology</source>
  </thought>
  <thought cid="cid:blake3:parent456">
    <type>git/commit</type>
    <content>Initial commit</content>
    <because/>
    <source>git/wot-technology</source>
  </thought>
</thought_context>
```

The LLM receives structured provenance, not just text. It can reason about WHY thoughts exist and trace claims back to sources.

## Implementation Order

### Week 1: Foundation
- [ ] Core data structures (Thought, Cid, etc)
- [ ] CID computation
- [ ] SQLite schema + basic store
- [ ] Simple CLI skeleton

### Week 2: Git Adapter
- [ ] Commit walking with git2-rs
- [ ] Commit → Thought transform
- [ ] Parent → because mapping
- [ ] Basic identity handling

### Week 3: Query Basics
- [ ] FTS5 integration
- [ ] Basic search CLI
- [ ] Chain walking

### Week 4: Integration
- [ ] MCP server
- [ ] REST API
- [ ] Vector embeddings (optional, depends on needs)

### Week 5+: Additional Adapters
- [ ] Wiki adapter
- [ ] Sitemap adapter
- [ ] Obsidian/Roam adapters

## Testing Strategy

### Unit Tests
- CID computation determinism
- Thought validation
- Transform correctness

### Integration Tests
- Index a known git repo, verify thought count
- Query and verify results
- Chain walking correctness

### Corpus Tests
- Index WoT spec repo → query for concepts
- Index a wiki → verify link extraction
- Performance on large repos (Linux kernel?)

## Open Questions

1. **CID format migration**: Existing corpus mixes `cid:sha256:` and `cid:blake3:`. Indexer should handle both. New content uses BLAKE3.

2. **Granularity**: Should every file change be a thought, or just commits? Git commits are natural boundaries; file diffs might be too noisy for most queries.

3. **External references**: How to handle `because` links to content outside the corpus? Options:
   - Stub thoughts with `type: "external/url"` 
   - Leave dangling (mark as unresolvable)
   - Fetch and index on demand

4. **Identity bootstrapping**: The indexer itself needs an identity to sign thoughts. Ship with:
   - Anonymous indexer identity (for testing)
   - Ceremony to adopt indexed content under real identity

5. **Trust bootstrapping**: Who attests to the indexer's output? Options:
   - User attests after review
   - Pool-level "this was indexed by tool X" marker
   - No attestation until human reviews

6. **Source attribution hierarchy**: Git has author email. Wiki has username. How granular?
   ```
   source: "git/wot-technology/keif@example.com"
   source: "wiki/wikipedia/User:ExampleEditor"
   ```

7. **Incremental updates**: How to efficiently re-index when source changes? Track last indexed commit SHA / page revision.

8. **Connection to now.pub library pools**: Should indexer output schemas align with core library schemas at `wot://library/patterns`?

## Bootstrap: Library Pool Alignment

The because indexer should produce thoughts compatible with the library pool schemas at now.pub:

```
wot://library/patterns
├── schema/git-commit
├── schema/wiki-page  
├── schema/web-page
└── schema/external-ref
```

First indexer output = first corpus = validation that library schemas work for real data.

This creates a virtuous cycle:
1. Index real repos → validate schemas
2. Fix schemas → re-index
3. Publish working schemas to library
4. Others use library → find edge cases
5. Iterate

## Dependencies

```toml
[dependencies]
blake3 = "1.5"                    # Primary CID hash (v0.7)
sha2 = "0.10"                     # Fallback for legacy content
ed25519-dalek = "2.0"             # Signatures
git2 = "0.18"                     # Git repository access
rusqlite = { version = "0.31", features = ["bundled"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1.0", features = ["full"] }
axum = "0.7"                      # REST API
clap = { version = "4.0", features = ["derive"] }  # CLI
hex = "0.4"                       # CID encoding
chrono = "0.4"                    # Timestamps

# Optional
fastembed = "3.0"                 # Local embeddings for semantic search
```

## Success Criteria

1. Can index the WoT spec git repo and query for concepts
2. Can walk because chains to understand thought provenance
3. Can export context for LLM injection via MCP
4. Performance: 10,000 thoughts indexed in < 1 minute
5. Storage: < 100 bytes overhead per thought
6. Outputs valid JSONL matching existing corpus format (thoughts.jsonl)

## Connection to Broader Vision

The because indexer is the **bridge from existing knowledge to WoT format**:

```
EXISTING WORLD               INDEXER                 WOT WORLD
────────────────────────────────────────────────────────────────
Git repos          →                        →   git/commit thoughts
Wikis              →    Because Indexer     →   wiki/page thoughts  
Sitemaps           →                        →   web/page thoughts
────────────────────────────────────────────────────────────────
                                ↓
                        Corpus for testing
                        Training data with provenance
                        Bootstrap for daemon
                        Validation for library schemas
```

Once we can index existing knowledge with because chains:
- Daemon can query for relevant context
- LLMs get grounded claims, not free-floating text
- Corrections can trace back to sources
- Training data carries consent via source attribution

The indexer is infrastructure. The value is the trails it creates.

---

*This spec is itself a thought. Its because chain includes: WoT v0.7 spec, manifesto, existing corpus samples (thoughts.jsonl, traces.jsonl), 15+ hours of design sessions, and the insight that memory is traversal, not storage.*
