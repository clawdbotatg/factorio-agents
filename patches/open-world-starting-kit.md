# Starting-kit parity (match legality) — SOLVED IN PYTHON, NO PATCH NEEDED

Vanilla freeplay grants a starting kit; FLE strips the inventory on reset
(`fle_actions.reset` overwrites it via `set_inventory`), handicapping agents
vs any human run (WR-PACE §6 parity audit).

The clean lever: `FactorioInstance(inventory={...})` — the `inventory` kwarg
is applied by reset itself. `arena.py` passes the freeplay economic subset:

```python
inventory={"burner-mining-drill": 1, "stone-furnace": 1,
           "iron-plate": 8, "wood": 1}
```

(Two earlier Lua patch attempts — scenario control.lua and the injected
clear_entities tool — were reverted: reset's set_inventory overwrites
whatever Lua inserts.)

# Also: FLE_SEED env knob (seed policy, WR-PACE §6)

`fle/cluster/run_envs.py` `ComposeGenerator.map_gen_seed = 44340` →
`int(os.environ.get("FLE_SEED", "44340"))`. Lab keeps the pinned default;
match rolls a random seed at start and RECORDS it. Re-apply after uv sync.

# Also: docker-compose.yml is the REAL authority (not run_envs generator)

`fle/cluster/docker-compose.yml` command: seed comes from an inline
`echo {"seed":...} > map-gen-settings.json` (previously hardcoded 424242 —
the original pin) and the DLC dirs were rm -rf'd. Patched: seed is
`${FLE_SEED:-424242}` (compose env interpolation; export FLE_SEED before
`fle cluster start` for a random/match seed) and the DLC deletion is
REMOVED (Space Age mods enabled via mods/mod-list.json — but check whether
cluster start regenerates that file). Re-apply after uv sync.

# Also: placement legality gate (match rules)

`fle/env/tools/agent/place_entity/server.lua`: every `create_entity` is now
preceded by `fle_utils.can_place_entity` (manual build check) — raw
create_entity can stack entities on occupied tiles (bot built on the
human's structure in live match 3; self-entombment in match 1). Re-apply
after uv sync; REBAKE the scenario after patching (bake_scenario.py), but
never mid-match (handler identity breaks rejoins).

# Also: agent tools hardcode force="player" (breaks VS forces)

Multiple `fle/env/tools/agent/*/server.lua` (place_entity create path!,
inspect_inventory, pickup, rotate, connect) hardcode `force = "player"` —
a bot moved to another force still builds/searches on force player. Patched
to `force = player.force`. Re-apply after uv sync.

# Also: move_to phantom-arrival desync (the everything-fails bug)

`fle/env/tools/agent/move_to/client.py` (fast=False branch): after the
walking-queue wait, FLE set `player_location` to the REQUESTED target even
if the walk was aborted/cleared — every later build target then computes
out of reach from a phantom position and ALL placements fail (vs-race 4:
bot 0 builds in 40 min). Patched: read the character's real position via
RCON after every walk. Re-apply after uv sync.
