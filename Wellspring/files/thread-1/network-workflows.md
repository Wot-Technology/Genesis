# WoT Network Workflows

**Status:** Draft
**Thread:** 1 (RFC)
**Version:** 0.1

---

## Transport Stack

```
┌─────────────────────────────────────────────────────────────┐
│  APPLICATION: Thoughts, Attestations, Connections           │
├─────────────────────────────────────────────────────────────┤
│  SERIALIZATION: Protobuf (compiled from WoT schemas)        │
├─────────────────────────────────────────────────────────────┤
│  FRAMING: 96-byte WoT header + payload + signature          │
├─────────────────────────────────────────────────────────────┤
│  RPC: gRPC (request/response, streaming)                    │
├─────────────────────────────────────────────────────────────┤
│  TRANSPORT: QUIC / TCP / Tor                                │
├─────────────────────────────────────────────────────────────┤
│  NETWORK: IPv4 / IPv6 / .onion                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Schema Compilation

WoT schemas (thoughts) compile to protobuf descriptors:

```
WoT Schema Thought                    Compiled Protobuf
──────────────────                    ─────────────────

{                                     message BasicThought {
  "schema": "basic",                    string type = 1;
  "version": "1.0.0",                   string content = 2;
  "fields": {                           bytes created_by = 3;
    "content": {                        repeated bytes because = 4;
      "type": "string",                 int64 created_at = 5;
      "required": true                  bytes signature = 6;
    }                                 }
  }
}
```

**Compilation rules:**

| WoT Type | Protobuf Type |
|----------|---------------|
| `string` | `string` |
| `integer` | `int64` |
| `float` | `double` |
| `boolean` | `bool` |
| `cid` | `bytes` (36) |
| `array[T]` | `repeated T` |
| `object` | `message` (nested) |
| `enum` | `enum` |
| `any` | `google.protobuf.Any` |

**Schema CID → Proto descriptor:**
- Each schema CID maps to a compiled .proto
- Nodes cache compiled descriptors
- Unknown schema? Fetch the thought, compile, cache

---

## Workflow 1: Discovery

Find a pool to join.

```
SOURCES
───────
1. DNSSEC:     keif.now.pub TXT → pool CID
2. IPNS:       /ipns/<peer-id>/pools → pool list
3. Direct:     Friend sends pool CID
4. Gossip:     Ask trusted peers for pools matching topic

RESOLUTION
──────────
Pool CID → Fetch intro thought → Read pool_rules → Decide to join
```

---

## Workflow 2: Handshake

Establish peering with a pool member.

### Packet Types

| Type | Code | Compression | Direction |
|------|------|-------------|-----------|
| HELLO | 0x01 | lz4 | → |
| HELLO_ACK | 0x02 | lz4 | ← |
| HELLO_NAK | 0x03 | lz4 | ← |
| SCHEMA_REQ | 0x10 | lz4 | → |
| SCHEMA_RESP | 0x11 | lz4 | ← |
| JOIN_REQ | 0x20 | lz4 | → |
| JOIN_ACK | 0x21 | lz4 | ← |
| JOIN_NAK | 0x22 | lz4 | ← |
| PEER_READY | 0x30 | lz4 | ↔ |
| PEER_ABORT | 0x31 | lz4 | ↔ |

### Sequence

```
INITIATOR                              RECEIVER
─────────                              ────────

┌──────────────────────────────────────────────────────────────┐
│ PHASE 1: IDENTITY EXCHANGE                                    │
└──────────────────────────────────────────────────────────────┘

1. HELLO ─────────────────────────────►
   │ my_identity_cid
   │ protocol_version: 0x0001
   │ capabilities: [schemas, compression, ...]
   │ timestamp
   │ signature
                                       2. Verify signature
                                          Check protocol version
                                          Check capabilities overlap

                                       3. ◄───────────────── HELLO_ACK
                                          │ your_identity_cid
                                          │ accepted_capabilities
                                          │ session_id
                                          │ signature

┌──────────────────────────────────────────────────────────────┐
│ PHASE 2: SCHEMA NEGOTIATION                                   │
└──────────────────────────────────────────────────────────────┘

4. SCHEMA_REQ ────────────────────────►
   │ pool_cid
   │ "what schemas must I support?"

                                       5. ◄─────────────── SCHEMA_RESP
                                          │ pool_rules_cid
                                          │ required_schemas: [cid, cid, ...]
                                          │ schema_protos: [compiled descriptors]
                                          │ rate_limits
                                          │ timestamp_unit

6. Local validation:
   │ Can I produce these schemas?
   │ Do I have/can compile the protos?
   │ Can I meet rate limits?
   │
   ├─► NO  → PEER_ABORT "incompatible" ────►
   │
   └─► YES → continue

┌──────────────────────────────────────────────────────────────┐
│ PHASE 3: JOIN REQUEST                                         │
└──────────────────────────────────────────────────────────────┘

7. JOIN_REQ ──────────────────────────►
   │ pool_cid
   │ my_identity_cid
   │ referrer_cid (if any)
   │ requested_chains: [cid, ...]
   │ introduction: "why I want to join"
   │ join_request_thought_cid
   │ signature

                                       8. Check join policy:
                                          │ open? → accept
                                          │ expected_only? → check expectations
                                          │ invite_only? → verify referrer
                                          │ attested? → check attestation count
                                          │
                                          ├─► REJECT
                                          │   ◄──────────────── JOIN_NAK
                                          │   │ reason
                                          │   │ retry_after (optional)
                                          │
                                          └─► ACCEPT
                                              Create: member thought
                                              Create: chain_access thoughts
                                              Create: peering thought

                                       9. ◄─────────────── JOIN_ACK
                                          │ member_thought_cid
                                          │ chain_access_cids: [...]
                                          │ peering_thought_cid
                                          │ signature

┌──────────────────────────────────────────────────────────────┐
│ PHASE 4: BILATERAL CONFIRMATION                               │
└──────────────────────────────────────────────────────────────┘

10. Create my peering thought
    (references their peering thought)

11. PEER_READY ───────────────────────►
    │ my_peering_thought_cid
    │ sync_filter_cid (optional)
    │ signature

                                       12. ◄───────────── PEER_READY
                                           │ ack
                                           │ their_sync_filter_cid

═══════════════════════════════════════════════════════════════
                    PEERING ESTABLISHED
                    Begin sync workflow
═══════════════════════════════════════════════════════════════
```

---

## Workflow 3: Schema Exchange Detail

Before syncing, validate we can handle each other's thoughts.

### SCHEMA_REQ Payload (protobuf)

```protobuf
message SchemaRequest {
  bytes pool_cid = 1;                    // Pool we're joining
  repeated bytes known_schemas = 2;      // Schemas we already have
  uint32 max_proto_size = 3;             // Max compiled proto we can accept
}
```

### SCHEMA_RESP Payload (protobuf)

```protobuf
message SchemaResponse {
  bytes pool_rules_cid = 1;              // Pool rules thought
  repeated SchemaBundle required = 2;    // Schemas we must support
  RateLimits rate_limits = 3;
  string timestamp_unit = 4;             // "s" | "ms" | "us" | "ns"
}

message SchemaBundle {
  bytes schema_cid = 1;                  // WoT schema thought CID
  bytes proto_descriptor = 2;            // Compiled protobuf descriptor
  uint32 proto_version = 3;              // Proto syntax version
}

message RateLimits {
  uint32 thoughts_per_minute = 1;
  uint32 bytes_per_minute = 2;
  uint32 max_payload_bytes = 3;
}
```

### Validation Logic

```
ON SCHEMA_RESP:

1. For each required schema:
   │
   ├─► Already have compiled proto?
   │     → Use cached
   │
   ├─► Have WoT schema thought but no proto?
   │     → Compile locally, verify matches received
   │
   ├─► Don't have schema thought?
   │     → Fetch from peer or IPFS
   │     → Compile
   │     → Cache
   │
   └─► Can't compile / incompatible?
       → PEER_ABORT "schema_incompatible"

2. For each schema, verify:
   │
   ├─► Can produce thoughts matching this schema?
   ├─► Have required field encoders?
   └─► Proto descriptor parses correctly?

3. Check rate limits:
   │
   ├─► thoughts_per_minute achievable?
   ├─► bytes_per_minute reasonable?
   └─► max_payload_bytes acceptable?

4. All checks pass?
   → Continue to JOIN_REQ
```

---

## Workflow 4: Sync

Exchange thoughts after peering established.

### Packet Types

| Type | Code | Compression | Direction |
|------|------|-------------|-----------|
| BLOOM | 0x40 | lz4 | ↔ |
| WANT | 0x41 | lz4 | ↔ |
| THOUGHT | 0x50 | zstd | ↔ |
| THOUGHT_ACK | 0x51 | lz4 | ↔ |
| THOUGHT_NAK | 0x52 | lz4 | ↔ |

### Bloom Filter Exchange

```
INITIATOR                              RECEIVER
─────────                              ────────

1. Build bloom filter of my CIDs
   (filtered by: pool, visibility, sync_filter)

2. BLOOM ─────────────────────────────►
   │ filter_bytes
   │ filter_params: {k, m, hash_algo}
   │ thought_count
   │ timestamp

                                       3. Check bloom for each local CID
                                          Identify: they_need = mine - theirs

                                       4. ◄───────────────────── BLOOM
                                          │ their filter_bytes
                                          │ filter_params
                                          │ thought_count

5. Check their bloom for each local CID
   Identify: i_need = theirs - mine

6. WANT ──────────────────────────────►
   │ cids: [what I need from them]
   │ priority: [high, normal, low]

                                       7. ◄──────────────────────── WANT
                                          │ cids: [what they need from me]
                                          │ priority

8. For each CID they want:              9. For each CID I want:
   THOUGHT ─────────────────────►          ◄──────────────────── THOUGHT
   │ thought (protobuf-encoded)            │ thought
   │ schema_cid                            │ schema_cid
   │ signature                             │ signature
```

### Bloom Filter Parameters

```
Optimal for 10k thoughts, 1% false positive:
  m = 95,851 bits (~12 KB)
  k = 7 hash functions

Scalable:
  m = -n * ln(p) / (ln(2)^2)
  k = (m/n) * ln(2)

Where:
  n = expected thought count
  p = desired false positive rate
  m = filter size in bits
  k = number of hash functions
```

### THOUGHT Payload

```protobuf
message ThoughtPayload {
  bytes schema_cid = 1;              // Schema for this thought
  bytes thought_cbor = 2;            // Canonical CBOR (for CID verification)
  bytes thought_proto = 3;           // Protobuf-encoded (for fast parse)
  bytes signature = 4;               // Ed25519 over CID
}
```

**Dual encoding rationale:**
- `thought_cbor`: Canonical, for CID verification (hash this)
- `thought_proto`: Fast parse, for processing (use this)
- Receiver verifies: `blake3(thought_cbor) == expected CID`

---

## Workflow 5: Thought Validation (Receiver)

```
RECEIVE THOUGHT PACKET
        │
        ├─► 1. Decompress (zstd)
        │
        ├─► 2. Parse protobuf envelope
        │      Extract: schema_cid, thought_cbor, thought_proto, signature
        │
        ├─► 3. Verify CID
        │      computed = blake3(thought_cbor)
        │      expected = extract from thought_proto
        │      MUST match
        │
        ├─► 4. Lookup schema
        │      Known? → use cached proto descriptor
        │      Unknown? → fetch, compile, cache (or reject)
        │
        ├─► 5. Parse thought_proto against schema
        │      Validates all required fields present
        │      Types match schema
        │
        ├─► 6. Verify signature
        │      Extract created_by from thought
        │      Lookup identity pubkey
        │      Verify ed25519(signature, cid)
        │      Invalid? → HARD REJECT
        │
        ├─► 7. Check pool rules
        │      Schema in accept list?
        │      Size under limit?
        │      Rate limit ok?
        │      require_because satisfied?
        │
        ├─► 8. Store thought
        │      Index by CID
        │      Link to pool
        │
        ├─► 9. Create appetite_note
        │      Check chain_access
        │      Set: welcomed | unauthorized_claim | etc.
        │
        ├─► 10. Auto-annotate (if pool_rules specify)
        │       Generate summary
        │       Extract links
        │       Detect language
        │
        └─► 11. THOUGHT_ACK ───────────────────►
               │ cid
               │ status: accepted | flagged | quarantined
```

---

## Workflow 6: Maintenance

Ongoing peer health and updates.

### Packet Types

| Type | Code | Compression | Direction |
|------|------|-------------|-----------|
| HEARTBEAT | 0x60 | none | ↔ |
| SCHEMA_UPDATE | 0x61 | lz4 | ↔ |
| ATTESTATION | 0x62 | lz4 | ↔ |
| PEER_CLOSE | 0x6F | lz4 | ↔ |

### Heartbeat

```protobuf
message Heartbeat {
  uint64 timestamp = 1;
  uint32 thought_count = 2;        // Current pool thought count
  uint32 pending_sync = 3;         // Thoughts waiting to send
  bytes last_cid = 4;              // Most recent thought CID
}
```

Interval: 30 seconds default. Configurable per peering agreement.

### Schema Update

When pool adds new required schema:

```
PEER_A                                 PEER_B
──────                                 ──────

Pool admin adds schema requirement
        │
        └─► SCHEMA_UPDATE ────────────►
            │ pool_cid
            │ new_schema_cid
            │ proto_descriptor
            │ effective_at

                                       Compile and cache
                                       Update validation rules

                                       ◄──────────────── ACK
```

---

## Error Handling

### NAK Reasons

```protobuf
enum NakReason {
  UNKNOWN = 0;
  PROTOCOL_MISMATCH = 1;
  IDENTITY_INVALID = 2;
  SIGNATURE_INVALID = 3;
  SCHEMA_UNKNOWN = 4;
  SCHEMA_INCOMPATIBLE = 5;
  RATE_LIMITED = 6;
  POOL_CLOSED = 7;
  NOT_EXPECTED = 8;
  ATTESTATION_REQUIRED = 9;
  INTERNAL_ERROR = 99;
}
```

### Retry Logic

| Error | Retry? | Backoff |
|-------|--------|---------|
| RATE_LIMITED | Yes | Exponential, respect retry_after |
| SCHEMA_UNKNOWN | Yes | Fetch schema, then retry |
| NOT_EXPECTED | Maybe | Request expectation from pool admin |
| SIGNATURE_INVALID | No | Permanent failure |
| PROTOCOL_MISMATCH | No | Upgrade client |

---

## gRPC Service Definition

```protobuf
service WotPeer {
  // Handshake
  rpc Hello(HelloRequest) returns (HelloResponse);
  rpc GetSchemas(SchemaRequest) returns (SchemaResponse);
  rpc Join(JoinRequest) returns (JoinResponse);
  rpc ConfirmPeer(PeerReadyRequest) returns (PeerReadyResponse);

  // Sync
  rpc ExchangeBloom(BloomRequest) returns (BloomResponse);
  rpc Want(WantRequest) returns (stream ThoughtPayload);
  rpc Push(stream ThoughtPayload) returns (stream ThoughtAck);

  // Maintenance
  rpc Heartbeat(HeartbeatRequest) returns (HeartbeatResponse);
  rpc UpdateSchema(SchemaUpdateRequest) returns (Ack);
  rpc Close(CloseRequest) returns (Ack);
}
```

---

## Security Considerations

1. **All packets signed:** Header + payload covered by ed25519 signature
2. **Replay protection:** Timestamp + session_id in handshake
3. **Rate limiting:** Enforced per peer, per pool
4. **Schema validation:** Reject malformed payloads before processing
5. **CID verification:** Always verify content matches claimed CID
6. **Chain access:** Check before surfacing, annotate if unauthorized

---

## Load Balancing Strategy

### Client-Side Load Balancing (Preferred)

WoT uses client-side load balancing for peer connections:

```
CLIENT                              PEERS
──────                              ─────

Resolve DNS/IPNS ──────────────►   Peer A (now.pub CDN)
                                    Peer B (friend's node)
Maintain connections to all ◄──►   Peer C (community relay)

Distribute requests:
├── Round-robin for sync
├── Trust-weighted for queries
└── Closest for latency-sensitive
```

**Why client-side, not proxy:**

| Factor | Proxy LB | Client-Side LB |
|--------|----------|----------------|
| Latency | +1 hop | Direct |
| SPOF | Proxy is SPOF | No SPOF |
| Trust model | Untrusted clients | Peer network (trusted) |
| State | Proxy tracks backends | Client tracks peers |
| WoT fit | ❌ | ✓ |

**WoT-specific advantages:**

1. **Eventual consistency:** All peers get all content eventually. No "owner" — safe to distribute requests.

2. **Commit-only model:** Append-only thoughts, no conflicts. Any peer can accept a write.

3. **Trust-weighted selection:** Client picks peers based on attestation weight, not random. Trust graph IS the load balancer.

4. **Resilience:** If one peer is down, client automatically uses others. No proxy to fail.

### Discovery + Distribution

```
1. DISCOVERY (DNS/IPNS)
   ├── Resolve now.pub TXT records
   ├── Resolve IPNS peer list
   └── Query trusted peers for more

2. CONNECTION
   ├── Maintain gRPC channels to N peers
   ├── Periodic health checks
   └── Reconnect on failure

3. REQUEST DISTRIBUTION
   ├── SYNC: Round-robin (all peers need all data)
   ├── QUERY: Trust-weighted (prefer high-attestation peers)
   └── PUSH: Fanout to all (or subset based on pool rules)
```

### gRPC Client Configuration

```go
// Example: Go client with round-robin + health checks
conn, err := grpc.Dial(
    "dns:///peers.now.pub:443",
    grpc.WithDefaultServiceConfig(`{
        "loadBalancingPolicy": "round_robin",
        "healthCheckConfig": {
            "serviceName": "wot.WotPeer"
        }
    }`),
)
```

### Trust-Weighted Balancing

For queries where response quality matters:

```
score(peer) = attestation_weight × uptime × (1 / latency)

Select peer with probability proportional to score
```

This isn't random load balancing — it's **reputation-weighted routing**.

---

## Implementation Notes

### Recommended Libraries

| Language | gRPC | Protobuf | BLAKE3 | Ed25519 |
|----------|------|----------|--------|---------|
| Rust | tonic | prost | blake3 | ed25519-dalek |
| Python | grpcio | protobuf | blake3 | pynacl |
| Go | grpc-go | protobuf | zeebo/blake3 | crypto/ed25519 |
| TypeScript | @grpc/grpc-js | protobufjs | @aspect/blake3 | @noble/ed25519 |

### Performance Targets

| Operation | Target |
|-----------|--------|
| Handshake complete | < 100ms |
| Bloom exchange (10k thoughts) | < 50ms |
| Thought validation | < 1ms |
| Schema compilation | < 100ms (cached: < 1ms) |
