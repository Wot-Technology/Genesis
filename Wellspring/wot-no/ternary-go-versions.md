# Go San & No — Version History

## Current Releases

### Go San 碁三 (Tactical)
**File:** go-san.html
- Void inversion: sacrifice your stone to create void
- 3×3 bounded spread — max 9 squares per nuke
- Tick spread: clockwise, one step per turn
- Tagline: *Sōgo — it takes two*

### No 無 (MAD)
**File:** no.html  
- Same mechanics, unlimited spread
- Games often end in mutual destruction
- Tagline: *The only winning move is not to play*

---

## Documentation

| File | Purpose |
|------|---------|
| go-san-rules.md | Physical play rules with resolver tokens |
| go-san-wot-handover.md | WoT protocol integration spec |

---

## Archived Versions

**v3** — ternary-go-v3-fast-scan.html
- Scan spread (always finds first valid spot) — too aggressive

**v1, v2** — not saved
- v1: Free void placement (spite problem)
- v2: Inversion cost + tick spread + infinite (void overrun)

---

## Design Evolution

1. Started exploring "unsolvable games" via three-body dynamics
2. Landed on ternary Go with void as third state
3. Free void placement → spite moves from losing positions
4. Added inversion cost (sacrifice own stone)
5. Unlimited spread still too aggressive
6. Fast scan spread → way too fast
7. 3×3 bounded spread → Go San (tactical)
8. Unlimited tick spread as separate variant → No (MAD)
9. Added gameEnded flag to prevent post-game bugs
10. Fixed board layout (pieces on intersections)
11. Renamed: Ternary Go → Go San, tagged as Sōgo

---

## Key Mechanics

### Void Inversion
- Must sacrifice YOUR OWN stone
- Can't nuke empty space or opponent
- Prevents spite plays from collapsed positions

### Tick Spread
- Pointer advances one direction per turn (N→NE→E→...)
- Spreads if target empty (and within 3×3 for Go San)
- New voids spawn pointing North

### Physical Play
- Resolver tokens toggle on/off each turn
- Odd turns: remove to process
- Even turns: add to process
- No reset phase needed

---

*Keif Gwinn & Claude, January 2026*
