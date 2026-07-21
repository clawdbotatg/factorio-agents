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
