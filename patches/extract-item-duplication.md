# Patch: extract_item item-duplication bug (2026-07-21)

**File:** `fle/env/tools/agent/extract_item/server.lua` (patched in the live
`.venv` AND `fle-patched-snapshot/`; re-apply after any FLE reinstall —
`diff` the two to check).

## The bug (two compounding halves)

1. `get_entity_item_count` looped over ~30 inventory types and added
   `entity.get_item_count(item)` — an **entity-wide** count — once per valid
   inventory, inflating availability 3–5× for furnaces.
2. The extraction tail removed what the entity actually had but inserted the
   **requested** stack into the player:
   `player.insert(stack)` where `stack.count = extract_count` (the request),
   not `number_extracted` (reality). Any request above actual contents
   **minted the difference from nothing**.

## Blast radius

`keep_fed` sweeps request `quantity=50` per furnace, so every legal-mode run
ever recorded minted plates on most sweeps (caught red-handed in
route-g110:L0: fed 48 ore, swept 100 plates). All historical production
numbers are inflated; night-1/night-2 route-search economics were invalid
(routes optimized to farm the dupe). Production *stats* only counted real
smelts — which is how the anomaly was spotted (power built with 24 plates
"produced" vs a 52-plate floor, S1-BIBLE §1).

## The fix

- `get_entity_item_count` → single `entity.get_item_count(item_name)`.
- Insert what was removed: `player.insert({name=..., count=number_extracted})`.

## Verification (probe_dupe_audit.py, 2026-07-21)

- Feed 10 ore, wait 40 game-s, request 50 plates → **received exactly 6**
  (what the furnace had smelted). Duplication dead.
- Craft conservation: 31 plates → craft steam engine attempts → final
  inventory 10 pipe + 9 gear + 3 plate = exactly 31 Fe. **craft_item never
  mints** (vanilla begin_crafting underneath). Separate quirk found: the
  craft recursion re-queues intermediates on retry, so an *exact* budget
  overcrafts parts and strands itself — budget slack above the S1-BIBLE §1
  recipe floors (and consider a future craft_item fix: don't re-queue
  intermediates already in the handcraft queue).
