# Prompt: Anthropic Conversation → WoT Thought Adapter + MCP Server

## Objective

Build an MCP server and adapter that ingests Anthropic conversation transcripts (the internal JSON format Claude produces) and maps each block to WoT (Web of Thought) protocol thoughts. The result is a content-addressed, signed, because-chained thought graph of every conversation — reasoning, responses, tool calls, and human input included.

This is the **fourth indexer** in the WoT architecture (after git, wiki, filesystem). It follows the same adapter pattern: source-specific input → WoT thoughts → thought store → MCP exposure.

---

## Source Format: Anthropic Conversation Transcript

Conversations are serialized as alternating `Human:` / `Assistant:` turns, each containing a JSON array of typed content blocks.

### Assistant Turn Block Types

```json
{
  "start_timestamp": "2026-02-01T14:42:13.415318Z",
  "stop_timestamp": "2026-02-01T14:42:14.499063Z",
  "flags": null,
  "type": "thinking",
  "thinking": "Full reasoning text...",
  "summaries": [
    { "summary": "Compressed representation of thinking." }
  ],
  "cut_off": false,
  "alternative_display_type": null
}
```

```json
{
  "start_timestamp": "2026-02-01T14:42:14.720384Z",
  "stop_timestamp": "2026-02-01T14:42:26.612269Z",
  "type": "tool_use",
  "id": "toolu_019693LLKrYKMhQVZfhZkHU2",
  "name": "str_replace",
  "input": {
    "path": "/home/claude/wot-v0.9-integrations.md",
    "old_str": "...",
    "new_str": "...",
    "description": "Add DNS section"
  },
  "message": "Add DNS as Thought Transport section",
  "display_content": {
    "type": "text",
    "text": "Add DNS as Thought Transport section"
  }
}
```

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_019693LLKrYKMhQVZfhZkHU2",
  "name": "str_replace",
  "content": [
    {
      "type": "text",
      "text": "Successfully replaced string in /home/claude/wot-v0.9-integrations.md",
      "uuid": "8ee2fb15-714b-4aef-ac9b-ff7761f7ca84"
    }
  ],
  "is_error": false
}
```

```json
{
  "start_timestamp": "2026-02-01T18:58:14.123456Z",
  "stop_timestamp": "2026-02-01T18:58:45.789012Z",
  "type": "text",
  "text": "The response text visible to the user...",
  "citations": [
    {
      "url": "https://example.com/article",
      "title": "Source Article",
      "indices": [0, 3]
    }
  ]
}
```

### Human Turn Block Types

```json
{
  "start_timestamp": "2026-02-01T18:58:09.013182Z",
  "stop_timestamp": "2026-02-01T18:58:09.013182Z",
  "type": "text",
  "text": "The human's message...",
  "citations": []
}
```

### Key Observations

- `tool_use.id` links to `tool_result.tool_use_id` — this is an implicit `because` chain
- `thinking` blocks have `summaries` — these are lossy compressions of full reasoning
- `start_timestamp` / `stop_timestamp` give duration (reasoning time, generation time)
- `citations` on text blocks are already ContentRef-shaped (URL + indices)
- `cut_off` on thinking blocks indicates truncated reasoning
- Human turns have `start_timestamp == stop_timestamp` (instant, no generation time)
- Each turn is an ordered array of blocks — sequence matters for `because` ordering

---

## Target Format: WoT Thought

```rust
struct Thought {
    cid: Cid,                    // BLAKE3 hash of canonical content
    r#type: String,              // Schema type identifier
    content: Value,              // Type-specific payload
    created_by: Cid,             // Identity CID
    created_at: i64,             // Unix timestamp milliseconds
    source: Option<Cid>,         // Input attribution (connection to input schema)
    because: Vec<ContentRef>,    // Provenance chain
    signature: Signature,        // Ed25519 over canonical form
}
```

```rust
struct ContentRef {
    thought_cid: Cid,
    segment_cid: Option<Cid>,
    anchor: Option<TextSelector>,
    path: Option<String>,
    temporal: Option<(f64, f64)>,
}
```

---

## Schema Definition: `schema/anthropic_conversation`

Define a WoT schema that describes the Anthropic conversation block types. This schema lives in the thought graph itself — it's a thought of type `schema`.

### Type Hierarchy

```
anthropic/conversation          — container for a full conversation
anthropic/turn                  — a human or assistant turn
anthropic/thinking              — model reasoning (content-layer encrypted)
anthropic/thinking_summary      — lossy compression of thinking (metadata-layer)
anthropic/response              — model text output visible to user
anthropic/tool_request          — model requesting tool execution
anthropic/tool_result           — tool execution result
anthropic/human_input           — human message
anthropic/citation              — source reference from model output
```

### Source Schemas (input attribution)

```
input/anthropic_model           — model-generated content
input/anthropic_thinking        — model reasoning process
input/human_chat                — human typing in chat interface
input/tool_execution            — tool runtime environment
```

---

## Block → Thought Mapping

### `type: "thinking"` → Two Thoughts

A thinking block produces TWO thoughts:

**1. Full thinking thought (content-layer encrypted)**
```json
{
  "type": "anthropic/thinking",
  "content": {
    "reasoning": "<full thinking text>",
    "cut_off": false,
    "duration_ms": 1084
  },
  "created_by": "<model_identity_cid>",
  "created_at": 1738417333415,
  "source": "<connection: model_identity → uses_input → input/anthropic_thinking>"
}
```

**2. Summary thought (metadata-layer, references full thinking via `because`)**
```json
{
  "type": "anthropic/thinking_summary",
  "content": {
    "summaries": ["Compressed representation of thinking."]
  },
  "created_by": "<model_identity_cid>",
  "created_at": 1738417333415,
  "because": [
    { "thought_cid": "<full_thinking_cid>" }
  ]
}
```

The summary is a **rework** of the full thinking — information deliberately destroyed. Connection type: `rework` from summary → full thinking.

**Layered encryption:** The full thinking thought is encrypted with the content key (C). The summary is encrypted with the metadata key (M). A structural indexer with only M can see that reasoning happened, how long it took, and the compressed summary — but not the actual reasoning. Full members with C can see both.

### `type: "text"` (assistant) → `anthropic/response`

```json
{
  "type": "anthropic/response",
  "content": {
    "text": "<response text>",
    "duration_ms": 32000
  },
  "created_by": "<model_identity_cid>",
  "created_at": 1738417334720,
  "source": "<connection: model_identity → uses_input → input/anthropic_model>",
  "because": [
    "<preceding_thinking_cid if exists>",
    "<human_input_cid that prompted this>"
  ]
}
```

**Citations** on the text block become additional `because` entries:

```json
{
  "thought_cid": "<cited_source_thought_cid>",
  "anchor": {
    "exact": "<quoted text>",
    "prefix": "...",
    "suffix": "..."
  }
}
```

If the citation references a URL not yet in the graph, create a placeholder thought of type `external/web_resource` with the URL as content.

### `type: "tool_use"` → `anthropic/tool_request`

```json
{
  "type": "anthropic/tool_request",
  "content": {
    "tool_name": "str_replace",
    "tool_use_id": "toolu_019693LLKrYKMhQVZfhZkHU2",
    "input": { "path": "...", "old_str": "...", "new_str": "..." },
    "description": "Add DNS section",
    "display_text": "Add DNS as Thought Transport section"
  },
  "created_by": "<model_identity_cid>",
  "created_at": 1738417334720,
  "source": "<connection: model_identity → uses_input → input/anthropic_model>",
  "because": [
    "<preceding_thinking_cid>"
  ]
}
```

Also create a **connection**:
```
tool_request_thought → request_attention → tool_identity
```

The model is asking the tool to do something. That's an attention request.

### `type: "tool_result"` → `anthropic/tool_result`

```json
{
  "type": "anthropic/tool_result",
  "content": {
    "tool_name": "str_replace",
    "result_text": "Successfully replaced string...",
    "is_error": false,
    "uuid": "8ee2fb15-..."
  },
  "created_by": "<tool_identity_cid>",
  "created_at": 1738417354286,
  "source": "<connection: tool_identity → uses_input → input/tool_execution>",
  "because": [
    { "thought_cid": "<tool_request_cid>" }
  ]
}
```

**Critical:** The `because` chain links tool_result → tool_request via the `tool_use_id` → `id` mapping. This is the most important provenance link — it traces every tool output to the reasoning that caused it.

### `type: "text"` (human) → `anthropic/human_input`

```json
{
  "type": "anthropic/human_input",
  "content": {
    "text": "<human's message>"
  },
  "created_by": "<human_identity_cid>",
  "created_at": 1738417889013,
  "source": "<connection: human_identity → uses_input → input/human_chat>"
}
```

Human inputs have `start_timestamp == stop_timestamp`. No generation duration. The `because` chain is empty unless the human is explicitly responding to something (which would need to be inferred from conversation flow — see Turn Sequencing below).

---

## Turn Sequencing → Connection Graph

Within a turn, blocks are ordered. Between turns, human input causes assistant output. Build connections:

### Within an Assistant Turn (ordered array)

```
thinking[0] → thinking[1]        (connection: sequence, "continued reasoning")
thinking[n] → tool_use[0]        (connection: causes, "reasoning led to tool call")
tool_result → thinking[n+1]      (connection: causes, "result informed next reasoning")
thinking[last] → text            (connection: causes, "reasoning produced response")
```

### Between Turns

```
human_input → assistant_thinking[0]   (connection: causes, "prompt triggered reasoning")
assistant_text → human_input           (connection: causes, "response prompted next input")
```

### Conversation-Level

```
anthropic/conversation thought
  ├── connection: contains → turn[0]
  ├── connection: contains → turn[1]
  └── ...
```

Each turn:
```
anthropic/turn thought
  ├── connection: contains → block[0]
  ├── connection: contains → block[1]
  └── ...
  content: { role: "human" | "assistant", sequence: 0 }
```

---

## Identity Model

Three identity types per conversation:

### Model Identity
```json
{
  "type": "identity",
  "content": {
    "name": "claude-opus-4-5-20250514",
    "provider": "anthropic",
    "model_family": "claude-4.5"
  }
}
```

**Problem:** The model doesn't currently have its own signing key. For now, sign with a session key derived from conversation metadata. Flag as `provenance: "claimed"` not `provenance: "verified"`. When model provenance lands (v0.10 spec Part 15), upgrade to verified signatures.

### Human Identity
```json
{
  "type": "identity",
  "content": {
    "name": "<from conversation metadata or config>"
  }
}
```

Signed with human's WoT identity key if available. Otherwise session key, flagged as claimed.

### Tool Identity
```json
{
  "type": "identity",
  "content": {
    "name": "str_replace",
    "tool_type": "computer_use"
  }
}
```

Each distinct tool name gets an identity. Tool results are signed by tool identity. Provenance: the tool executed in a specific environment — that's the `source` attribution.

---

## MCP Server Interface

The adapter produces thoughts. The MCP server exposes them. Standard WoT MCP tools:

### Tools to Expose

```
wot_conversation_ingest(transcript_path: string) → { conversation_cid: Cid, thought_count: u32 }
```
Parse a transcript file, produce all thoughts, store in graph.

```
wot_conversation_list() → [{ cid: Cid, created_at: i64, turn_count: u32, title: string }]
```
List ingested conversations.

```
wot_thought_get(cid: string) → Thought
```
Retrieve a single thought by CID.

```
wot_thought_search(query: string, type_filter?: string) → [Thought]
```
Search thoughts by content. Optional type filter (`anthropic/thinking`, `anthropic/response`, etc.).

```
wot_walk_because(cid: string, depth?: u32) → [Thought]
```
Walk the because chain backward from a thought. Returns the full provenance trail.

```
wot_walk_sequence(conversation_cid: string, turn?: u32) → [Thought]
```
Walk a conversation or turn in sequence order.

```
wot_connections(cid: string, relation?: string) → [Connection]
```
Get all connections from/to a thought. Optional relation filter.

```
wot_conversation_stats(cid: string) → ConversationStats
```
Stats: thinking time, response time, tool calls, turn count, token estimates.

### Live Capture Mode (stretch goal)

If the MCP server is running alongside an active conversation (e.g. in Claude Code), it could capture blocks as they're produced rather than from a transcript file:

```
wot_capture_start(session_id: string) → { status: "recording" }
wot_capture_block(block: json) → { thought_cid: Cid }
wot_capture_stop(session_id: string) → { conversation_cid: Cid }
```

This would allow real-time thought graph construction during development sessions.

---

## Layered Encryption for Thinking Blocks

Thinking blocks get special treatment. The full reasoning is content-layer (C key). The summary is metadata-layer (M key).

```
┌─────────────────────────────────┐
│ Metadata layer (M key)          │
│                                 │
│ type: anthropic/thinking        │
│ created_by: model_identity      │
│ created_at: timestamp           │
│ duration_ms: 1084               │
│ summary: "Compressed repr..."   │
│ cut_off: false                  │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Content layer (C key)       │ │
│ │                             │ │
│ │ reasoning: "Full thinking   │ │
│ │ text with all details..."   │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

A structural indexer (M only) can build a map of:
- When reasoning happened
- How long it took
- What it was roughly about (summary)
- What it led to (connections to tool_use, response)

Without ever seeing the actual reasoning. This mirrors how Anthropic currently handles extended thinking — you see summaries, not full content.

---

## Implementation Notes

### Transcript Parsing

The transcript format alternates:
```
Human:
Content:
[...json array of blocks...]

================================================================================
Assistant:
Content:
[...json array of blocks...]

================================================================================
```

Parse by splitting on the separator line, then identifying role from the preceding line. Each content block is a JSON array.

### CID Computation

Follow WoT spec: BLAKE3 hash of canonical JSON (sorted keys, no whitespace). The `cid` field is excluded from the hash input (it's the result of hashing). The `signature` field is excluded from the hash input (signed over the CID).

### tool_use_id Resolution

Build a lookup map during ingestion:
```python
tool_use_map = {}  # tool_use_id -> tool_request_thought_cid

# When processing tool_use block:
tool_use_map[block['id']] = thought.cid

# When processing tool_result block:
because_cid = tool_use_map[block['tool_use_id']]
```

### Timestamp Handling

- `start_timestamp` → `created_at` (parse ISO 8601 to Unix ms)
- `stop_timestamp - start_timestamp` → `duration_ms` in content
- Human blocks where start == stop: duration_ms = 0 (instant)

### Storage

Use the existing WoT thought store (sled or SQLite, per implementation spec Part 3). The adapter writes thoughts, the MCP server reads them. Same store the git and wiki adapters write to.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                  Anthropic Conversation Adapter               │
│                                                              │
│  ┌────────────────┐    ┌─────────────────────────────┐       │
│  │ Transcript File │───▶│ Parser                      │       │
│  │ (.txt / .json)  │    │ - Split turns               │       │
│  └────────────────┘    │ - Parse block arrays         │       │
│                        │ - Resolve tool_use_id links  │       │
│                        └──────────┬──────────────────┘       │
│                                   ▼                          │
│                        ┌─────────────────────────────┐       │
│                        │ Block Mapper                 │       │
│                        │ - thinking → 2 thoughts      │       │
│                        │ - text → response/input      │       │
│                        │ - tool_use → request         │       │
│                        │ - tool_result → result        │       │
│                        │ - citations → because refs   │       │
│                        └──────────┬──────────────────┘       │
│                                   ▼                          │
│                        ┌─────────────────────────────┐       │
│                        │ Connection Builder            │       │
│                        │ - Sequence within turns      │       │
│                        │ - Causation between turns    │       │
│                        │ - tool_use ↔ tool_result     │       │
│                        │ - Conversation containment   │       │
│                        └──────────┬──────────────────┘       │
│                                   ▼                          │
│                        ┌─────────────────────────────┐       │
│                        │ Transform Core               │       │
│                        │ - CID compute (BLAKE3)       │       │
│                        │ - Sign (session key)         │       │
│                        │ - Encrypt layers (M/C)       │       │
│                        └──────────┬──────────────────┘       │
│                                   ▼                          │
│                        ┌─────────────────────────────┐       │
│                        │ Thought Store                │       │
│                        └──────────┬──────────────────┘       │
│                                   ▼                          │
│                        ┌─────────────────────────────┐       │
│                        │ MCP Server                   │       │
│                        │ - ingest / list / get        │       │
│                        │ - search / walk / stats      │       │
│                        └─────────────────────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

---

## Language Choice

Rust preferred (consistent with WoT core). If prototyping speed matters, Python with FastMCP is acceptable for the MCP server layer, with Rust for CID computation and signing.

---

## Reference Files

The WoT v0.10 specification is the authoritative reference:
- **Core spec:** Thought structure, CID computation, identity, connections, attestations, schemas, because chains
- **Implementation spec:** Storage, indexer architecture, MCP server patterns, layered encryption, structural retrieval
- **Integrations spec:** Wire format, transport

Example transcript files are available in the conversation history for format reference.

---

## What Success Looks Like

After ingesting a conversation transcript:

1. Every thinking block → signed thought with CID, summary as separate metadata-layer thought
2. Every response → signed thought with because chain to the thinking that produced it
3. Every tool call → signed request + result pair linked by because
4. Every human input → signed thought attributed to human identity
5. Full conversation navigable as a thought graph via MCP tools
6. `wot_walk_because` from any response traces back through reasoning → human prompt → prior response → prior reasoning
7. `wot_conversation_stats` gives thinking time, response time, tool call count
8. Thinking content only accessible with content key; summaries visible with metadata key

The conversation becomes a first-class WoT artifact with full provenance, attribution, and access control.
