# Go San & No: A WoT Use Case

**Two-Player Adversarial Games as Attested Trails**

*A handover document for implementing Go San (碁三) and No (無) over the Wellspring of Thoughts protocol*

---

## Why This Matters for WoT

Games are the simplest case of multi-party state with consequences. Two players, adversarial goals, shared board, irreversible moves. If WoT can handle this cleanly, it can handle contracts, negotiations, collaborative documents — anything where multiple parties need to agree on what happened.

**No** in particular is a perfect metaphor for WoT's trust model:

- **The nuclear option has consequences** — you can launch it, but everyone sees you did, and you can't take it back
- **Mutual destruction is visible** — the trail shows who fired first
- **You can't deny the nuke** — your signature is on the move
- **Actions propagate** — the void spreads like information through a trust graph
- **Both players accountable** — Sōgo, it takes two

The game IS a trail. The trail IS the game. Same primitive.

---

## Game Overview

### Go San (碁三) — Tactical Variant

Standard 9×9 Go with one addition: **void inversion**.

- Convert your own stone to void (sacrifice material to create threat)
- Void spreads clockwise, one tick per turn
- **Bounded to 3×3** around origin — max 9 squares of damage
- Tactical, competitive, suitable for ranked play

### No (無) — MAD Variant

Same mechanics, one difference: **voids spread without limit**.

- Going nuclear often destroys both players
- Games frequently end in mutual devastation
- The threat of nuclear may be stronger than using it
- *"The only winning move is not to play... but can you trust your opponent?"*

---

## Mapping to WoT Primitives

### The Game as a Pool

```
Pool: go-san-game-{game_id}
  participants: [player_black, player_white]
  rules: "go-san-v1" | "no-v1"
  board_size: 9
  komi: 6.5
```

The pool is the game. Both players have write access. The pool rules define which variant.

### Moves as Thoughts

Every move is a Thought:

```yaml
thought:
  cid: Qm...  # content-addressed
  type: "go-san/move"
  content:
    game_id: "game-123"
    move_number: 42
    player: "black"
    action: "place" | "invert" | "pass"
    position: [4, 5]  # or null for pass
    board_state_hash: "sha256:..."  # hash of resulting board
  because:
    - Qm...previous_move  # the move this responds to
  created_by: "did:key:z6Mk...playerBlack"
  created_at: "2026-01-07T15:43:55Z"
  signature: "ed25519:..."
```

The `because` chain IS the game history. Walk backwards = replay the game.

### Attestation as Acknowledgment

When Black plays, White must attest to continue:

```yaml
attestation:
  cid: Qm...
  type: "go-san/ack"
  content:
    thought: Qm...blacks_move
    verdict: "valid"  # or "invalid" with reason
    board_state_confirmed: true
  created_by: "did:key:z6Mk...playerWhite"
  signature: "ed25519:..."
```

**No attestation = game paused.** Neither player can proceed without the other's acknowledgment. This prevents:
- Disputed board states
- "I didn't see that move" 
- Retroactive complaints

Both players sign every move. The trail is mutually attested.

### Void State as Structured Content

```yaml
void_state:
  position: [3, 4]
  pointer: 2  # 0=N, 1=NE, 2=E, etc.
  origin: [3, 4]  # for Go San 3×3 limit
  created_move: 23  # when this void was placed
```

The void's direction is part of the attested state. You can't claim the pointer was different — it's in the signed thought.

### Game End as Commitment

```yaml
thought:
  type: "go-san/result"
  content:
    game_id: "game-123"
    result: "white+3.5" | "black+resign" | "draw"
    final_score:
      black: 74
      white: 77.5
    void_count: 12
    move_count: 87
  because:
    - Qm...final_board_state
    - Qm...pass_by_black
    - Qm...pass_by_white
  attested_by:
    - { identity: player_black, verdict: "accept" }
    - { identity: player_white, verdict: "accept" }
```

Both players attest to the result. Disputes are visible in the attestation chain.

---

## Protocol Flow

### Game Setup

```
1. Player A creates pool with rules (go-san | no)
2. Player A invites Player B (share pool access)
3. Player B attests to rules acceptance
4. Game begins — Black plays first
```

### Turn Sequence

```
1. Current player creates move thought
   - References previous move in `because`
   - Includes resulting board state hash
   - Signs with their key

2. Move published to pool

3. Opponent receives move
   - Validates against rules (legal move?)
   - Validates board state hash
   - Creates attestation thought
   - Signs acknowledgment

4. Void resolution (if any voids exist)
   - Deterministic — both clients compute same result
   - New void positions included in next move's state

5. Turn passes to opponent
```

### Dispute Resolution

If a player attests `verdict: "invalid"`:

```yaml
attestation:
  content:
    thought: Qm...disputed_move
    verdict: "invalid"
    reason: "illegal_move"
    details: "suicide not allowed at [3,4]"
    proposed_state: Qm...correct_board_state
```

The dispute is in the trail. Third parties can audit by replaying the `because` chain.

---

## Implementation Notes

### Client Requirements

Each client must:

1. **Validate moves locally** — don't trust opponent's board state hash blindly
2. **Compute void spread deterministically** — same algorithm, same results
3. **Sign every move** — ed25519, same key as WoT identity
4. **Verify opponent signatures** — reject unsigned moves
5. **Maintain local board state** — derived from trail, not trusted from network

### Offline Play

WoT's append-only model supports async play:

- Player A moves, signs, publishes
- Player A goes offline
- Player B receives (whenever), validates, attests, moves
- Sync happens when both online

The trail is the source of truth. Clients reconstruct state from trail on reconnect.

### Spectator Mode

Third parties can subscribe to the pool read-only:

```
Pool: go-san-game-123
  participants: [black, white]  # write access
  spectators: [public]          # read access
```

Spectators see the attested trail in real-time. They can verify every move but can't inject thoughts.

---

## Why "No" Is the Killer Demo

The nuclear variant demonstrates WoT's core value proposition:

| Game Mechanic | WoT Parallel |
|---------------|--------------|
| Can't take back a move | Immutable append-only |
| Both players see same board | Shared attested state |
| Nuke has your name on it | Signed actions with consequences |
| Void spreads predictably | Deterministic state transitions |
| Both players lose to void | Mutual accountability |
| Can't deny you nuked | Cryptographic proof of action |
| Trust opponent to play fair | Protocol enforces rules |

**The tagline writes itself:**

> *"In No, you can launch the nukes. But your name is on the button, forever, in the chain. WoT doesn't prevent bad decisions — it makes them attributed."*

---

## Files Included

| File | Description |
|------|-------------|
| `go-san.html` | Browser-based Go San (3×3 bounded voids) |
| `no.html` | Browser-based No (unlimited voids, MAD) |
| `go-san-rules.md` | Physical play rules with resolver token system |

Current implementations are single-device. WoT integration replaces local state with pool sync.

---

## Next Steps

### Phase 1: Local Proof of Concept
- [ ] Define thought schemas for moves, attestations, results
- [ ] Implement move signing with ed25519
- [ ] Add signature verification to clients
- [ ] Export game as trail (JSON-LD or similar)

### Phase 2: Two-Player Sync
- [ ] Pool creation and invitation flow
- [ ] Real-time move subscription
- [ ] Attestation handshake per turn
- [ ] Disconnect/reconnect recovery

### Phase 3: Public Features
- [ ] Spectator subscriptions
- [ ] Game result attestation and publication
- [ ] Rating system via trust-weighted game outcomes
- [ ] Tournament pools with multi-game trails

---

## The Bet

If WoT can handle adversarial two-player games with:
- Shared mutable state
- Turn-based attestation
- Irreversible consequences
- Dispute auditability

...then it can handle anything that's "just" coordination with receipts.

Contracts. Approvals. Negotiations. Collaborative editing. Multi-agent workflows.

Start with a game. Prove the primitives. Scale to everything else.

---

*Go San (碁三) — Sōgo, it takes two*
*No (無) — The only winning move is not to play*

*Keif Gwinn & Claude*
*January 2026*

---

## Appendix: Board State Hashing

For deterministic verification, board state hash includes:

```
SHA256(
  board[81]         # 0=empty, 1=black, 2=white, 3=void
  void_pointers[n]  # direction for each void
  void_origins[n]   # origin position (Go San only)
  current_player    # 1=black, 2=white
  ko_point          # position or null
  consecutive_passes
  captures_black
  captures_white
)
```

Both clients compute this identically. Mismatch = dispute.

---

## Appendix: Void Spread Algorithm

```python
DIRECTIONS = [
    (-1, 0),   # N
    (-1, 1),   # NE
    (0, 1),    # E
    (1, 1),    # SE
    (1, 0),    # S
    (1, -1),   # SW
    (0, -1),   # W
    (-1, -1),  # NW
]

def spread_voids(board, voids, variant):
    new_voids = []
    
    for void in voids:
        direction = DIRECTIONS[void.pointer]
        target = void.position + direction
        
        # Check spread conditions
        can_spread = (
            target.in_bounds() and
            board[target] == EMPTY and
            (variant == "no" or target.within_3x3(void.origin))
        )
        
        if can_spread:
            new_voids.append(Void(
                position=target,
                pointer=0,  # new voids point North
                origin=void.origin  # inherit origin
            ))
        
        # Rotate pointer regardless
        void.pointer = (void.pointer + 1) % 8
    
    return new_voids
```

Deterministic. Same inputs = same outputs. Both clients run this after every move.
