# 無 No — Nuclear Go
# 碁三 Go San — Sōgo

## Two Go variants with void mechanics

---

## Components

- Standard Go stones (black & white)
- **Void tokens**: Small tokens with a directional arrow (rotatable)
- **Resolver tokens**: Small markers that stack on voids (one per void in play)
- 9×9 Go board (recommended for faster games)

---

## Setup

Standard Go setup. Black plays first. No voids on the board initially.

---

## Turn Structure

On your turn, do ONE of the following:

### A. Place a Stone
Place one of your stones on an empty intersection. Standard Go rules apply:
- Captures happen immediately (remove surrounded enemy groups)
- Suicide is not allowed (unless it captures)
- Ko rule is active

### B. Go Nuclear ☢️
Convert one of **your own stones** into a void:
1. Remove your stone from the board
2. Place a void token on that intersection, arrow pointing **North**

*You cannot nuke empty intersections or opponent's stones.*

### C. Pass
Pass your turn. Two consecutive passes end the game.

---

## Void Resolution Phase

After EVERY turn (including passes), process all voids:

### Resolver Toggle System

Each void can have a **resolver token** on it or not. The meaning alternates each turn:

- **Odd turns (1, 3, 5...)**: Resolvers ON = needs processing. Process → remove resolver.
- **Even turns (2, 4, 6...)**: Resolvers OFF = needs processing. Process → add resolver.

This eliminates any "reset" phase — the state carries over and flips meaning.

### For Each Unprocessed Void:
1. **Rotate** the void arrow one step clockwise (N→NE→E→SE→S→SW→W→NW→N...)
2. Check the intersection the arrow points to:
   - **If empty**: Place a new void there, arrow pointing North, with the "already processed" state (resolver if even turn, no resolver if odd turn)
   - **If blocked** (stone, void, or edge): Nothing happens
3. **Toggle** the resolver (remove if odd turn, add if even turn)

### Quick Check:
- Odd turn: "Any voids WITH resolvers?" → Process those
- Even turn: "Any voids WITHOUT resolvers?" → Process those
- When none remain in the "needs processing" state, resolution is complete

### New Voids:
Newly spawned voids always get the "already done" state for the current turn, so they wait until next turn to spread.

---

## Capture Cascade

After void resolution, check the entire board for groups with zero liberties:
- Voids **block liberties** (they are not empty space)
- Remove any captured groups
- Award captures to the opponent

This may trigger further captures — keep checking until stable.

---

## End of Game

The game ends when:
- Both players pass consecutively
- The board fills completely (rare)

### Scoring (Area Counting)
- **Territory**: Empty intersections surrounded by your colour only
- **Captures**: Stones you captured during the game
- **Komi**: White receives 6.5 points compensation
- **Void intersections**: Belong to neither player (dead territory)

Highest score wins.

---

## Quick Reference

| Action | Cost | Effect |
|--------|------|--------|
| Place stone | Your turn | Standard Go placement |
| Go nuclear | Your stone | Creates spreading void |
| Pass | Your turn | Voids still spread |

| Void behaviour | Rule |
|----------------|------|
| Spread direction | Clockwise tick each turn |
| Spread condition | Target must be empty |
| New void orientation | Always points North |
| Liberty blocking | Voids count as blocked (not empty) |
| Resolver toggle | Odd turns: remove to process. Even turns: add to process |
| New void state | Spawns in "already processed" state for current turn |

---

## Strategy Notes

- **Nuking costs material** — you sacrifice a stone to create chaos
- **Voids spread predictably** — you can calculate several turns ahead
- **Voids hurt everyone** — including you
- **Late-game nukes** can equalise a losing position
- **Early-game nukes** often backfire
- **The threat of nuclear** may be stronger than using it

---

## Variants

### Go San 碁三 (Controlled)
Each void only spreads within a **3×3 area** centered on where it was originally placed. Maximum 9 void squares per nuke. More tactical, less apocalyptic. *Sōgo — it takes two.*

### No 無 (Full MAD)
Voids spread without limit. Games often end in mutual destruction. Faster, more chaotic. Best for shorter sessions or making a point about nuclear deterrence. *The only winning move is not to play.*

---

## Physical Play Tips

1. Use coins with an arrow drawn in marker for void tokens
2. Use small chips (e.g., poker chips, bottle caps) as resolver tokens
3. Keep a turn counter or just remember: "last turn I removed, so this turn I add"
4. Newly spawned voids get the opposite resolver state from what you're processing
5. When in doubt about capture order: resolve voids first, then check captures

---

*"The only winning move is not to play... but can you trust your opponent?"*
