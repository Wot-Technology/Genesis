# WoT Dependency Licensing

**Status:** Tracking
**Updated:** 2026-01-31

---

## Summary

All core dependencies use permissive licenses (BSD, MIT, Apache 2.0, or public domain). No copyleft concerns.

| Dependency | License | Requirements | Notes |
|------------|---------|--------------|-------|
| **Protocol Buffers** | BSD 3-Clause + Apache 2.0 | Attribution | Runtime is Apache 2.0 for patent grant |
| **BLAKE3** | CC0 OR Apache 2.0 | None (CC0) or Attribution (Apache) | Dual license, user chooses |
| **gRPC** | Apache 2.0 | Attribution | Some components BSD 3-Clause |
| **libp2p** | MIT AND/OR Apache 2.0 | Attribution | Dual license varies by implementation |
| **Ed25519** | Varies by impl | Check specific lib | dalek-cryptography is BSD-3 |
| **CBOR** | Varies by impl | Check specific lib | cbor2 (Python) is MIT |

---

## Detailed Breakdown

### Protocol Buffers

**Source:** [github.com/protocolbuffers/protobuf](https://github.com/protocolbuffers/protobuf/blob/main/LICENSE)

**License:** BSD 3-Clause (core), Apache 2.0 (runtime)

**Why Apache for runtime:** Patent grant protection. From Google: "we need to use the Apache license because it contains language granting you permission to use any patents we might have on protocol buffers."

**Requirements:**
- Retain copyright notice
- Retain license text
- Retain disclaimer

**Generated code:** Inherits runtime license (Apache 2.0)

---

### BLAKE3

**Source:** [github.com/BLAKE3-team/BLAKE3](https://github.com/BLAKE3-team/BLAKE3/)

**License:** Dual-licensed CC0 1.0 (public domain) OR Apache 2.0

**Your choice:**
- CC0: No attribution required, truly public domain
- Apache 2.0: Attribution required, patent grant included

**Recommendation:** Use CC0 for simplicity. No obligations.

---

### gRPC

**Source:** [github.com/grpc/grpc](https://github.com/grpc/grpc/blob/master/LICENSE)

**License:** Apache 2.0

**Third-party components within gRPC:**
- address_sorting: BSD-3-Clause
- envoy-api: Apache-2.0
- googleapis: Apache-2.0
- upb: BSD-3-Clause
- utf8_range: MIT

**Requirements:**
- Include NOTICE file
- Retain copyright notices
- State changes if modified

---

### libp2p

**Source:** [github.com/libp2p](https://github.com/orgs/libp2p/repositories)

**License:** Dual MIT AND/OR Apache 2.0 (varies by implementation)

| Implementation | License |
|----------------|---------|
| go-libp2p | MIT |
| js-libp2p | Apache 2.0 OR MIT |
| rust-libp2p | Apache 2.0 OR MIT |
| py-libp2p | MIT AND Apache 2.0 |

**Requirements:** Attribution (whichever you choose)

---

### IPFS / Kubo

**Source:** [github.com/ipfs/kubo](https://github.com/ipfs/kubo)

**License:** Apache 2.0 AND MIT (dual)

**Requirements:** Attribution

---

### Ed25519 Implementations

| Library | Language | License |
|---------|----------|---------|
| ed25519-dalek | Rust | BSD-3-Clause |
| PyNaCl | Python | Apache 2.0 |
| noble-ed25519 | TypeScript | MIT |
| crypto/ed25519 | Go | BSD-3-Clause (Go license) |

---

### CBOR Implementations

| Library | Language | License |
|---------|----------|---------|
| cbor2 | Python | MIT |
| serde_cbor | Rust | MIT OR Apache 2.0 |
| cbor-x | JavaScript | MIT |

---

## License Compatibility Matrix

All our dependencies are compatible with each other and with common open-source licenses:

| WoT License Option | Compatible? | Notes |
|-------------------|-------------|-------|
| MIT | ✓ | All deps allow |
| Apache 2.0 | ✓ | All deps allow |
| BSD 3-Clause | ✓ | All deps allow |
| GPL v3 | ✓ | One-way compatible (can include, but WoT becomes GPL) |
| AGPL v3 | ✓ | One-way compatible (network use triggers) |
| Proprietary | ✓ | All permissive licenses allow |

---

## Recommended WoT License

**Options:**

1. **Apache 2.0** — Patent grant, clear contribution terms, corporate-friendly
2. **MIT** — Simple, maximally permissive, widely understood
3. **Dual MIT/Apache 2.0** — User chooses, covers all bases (Rust ecosystem standard)

**Recommendation:** **Dual MIT/Apache 2.0**

Rationale:
- Matches libp2p and Rust ecosystem conventions
- Apache 2.0 gives patent protection
- MIT gives simplicity for quick adoption
- No copyleft, allows proprietary use
- Clear contribution licensing

---

## Attribution Requirements

For binary distributions, include:

```
This software includes:
- Protocol Buffers, Copyright Google Inc., BSD-3-Clause/Apache-2.0
- gRPC, Copyright gRPC Authors, Apache-2.0
- BLAKE3, CC0/Apache-2.0
- libp2p, MIT/Apache-2.0
- [Additional libraries as used]

See LICENSES/ directory for full license texts.
```

---

## Tracking Checklist

- [ ] Finalize WoT license choice
- [ ] Create LICENSE file (or LICENSE-MIT + LICENSE-APACHE)
- [ ] Create NOTICE file with attributions
- [ ] Add license headers to source files
- [ ] Document in README
- [ ] Add SPDX identifiers to package metadata

---

## Sources

- [Protocol Buffers License](https://github.com/protocolbuffers/protobuf/blob/main/LICENSE)
- [BLAKE3 GitHub](https://github.com/BLAKE3-team/BLAKE3/)
- [gRPC License](https://github.com/grpc/grpc/blob/master/LICENSE)
- [libp2p Repositories](https://github.com/orgs/libp2p/repositories)
- [gRPC FAQ](https://grpc.io/docs/what-is-grpc/faq/)
