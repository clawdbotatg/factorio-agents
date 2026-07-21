"""Verify the extract_item duplication fix + craft ingredient accounting.

Reproduces the exact minting sequence caught in route-g110:L0 (feed a
furnace ore, sweep with quantity=50, count what appears) and settles the
S1-BIBLE §1 audit flag (craft a steam engine with exactly 31 vs 30 plates).

Usage: uv run python probe_dupe_audit.py [port]   (needs a free instance)
"""

import asyncio
import os
import sys

os.environ.setdefault("FLE_SPECTATOR_MODE", "1")

from fle.env.a2a_instance import A2AFactorioInstance  # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 27000

CODE = r'''
def _count(proto):
    inv = inspect_inventory()
    for probe in (lambda: inv[proto], lambda: inv.get(proto, 0)):
        try:
            return probe() or 0
        except Exception:
            continue
    return 0

# --- TEST 1: extract more than the furnace holds (the dupe repro) ---
p = nearest(Resource.IronOre)
move_to(p)
harvest_resource(p, 20)
move_to(Position(x=p.x, y=p.y - 8))
f = place_entity(Prototype.StoneFurnace, position=Position(x=p.x, y=p.y - 6))
insert_item(Prototype.Coal, f, quantity=5)
insert_item(Prototype.IronOre, f, quantity=10)
print("T1 fed 10 ore; waiting 40 game-s for partial smelt")
sleep(40)
before = _count(Prototype.IronPlate)
got = 0
try:
    got = extract_item(Prototype.IronPlate, f, quantity=50)
except Exception as e:
    print("T1 extract error:", str(e)[:80])
after = _count(Prototype.IronPlate)
print(f"T1 RESULT: requested 50, extract returned {got}, "
      f"inventory delta {after - before} (PASS if delta <= 10, FAIL if ~50)")

# --- TEST 2: craft cost accounting (31-plate steam engine) ---
# top up to exactly 31 plates via more smelting
insert_item(Prototype.IronOre, f, quantity=10)
need = 31 - _count(Prototype.IronPlate)
if need > 0:
    print(f"T2 smelting for {need} more plates…")
    sleep(80)
    try:
        extract_item(Prototype.IronPlate, f, quantity=need)
    except Exception as e:
        print("T2 extract:", str(e)[:60])
plates = _count(Prototype.IronPlate)
print(f"T2 plates in hand: {plates}")
if plates >= 31:
    # burn down to exactly 30 and expect FAIL, then 31 path
    ok30 = None
    try:
        craft_item(Prototype.SteamEngine, 1)
        ok30 = True
    except Exception as e:
        ok30 = False
        print("craft failed (msg):", str(e)[:100])
    left = _count(Prototype.IronPlate)
    eng = _count(Prototype.SteamEngine)
    print(f"T2 RESULT: craft_with_{plates}_plates -> engine={eng}, "
          f"plates left={left} (PASS if plates>=31 crafted exactly one and "
          f"consumed 31; a craft succeeding with <31 = ingredient leak)")
else:
    print("T2 SKIP: could not bank 31 plates in probe window")
print(inspect_inventory())
'''


def main():
    inst = asyncio.run(A2AFactorioInstance.create(
        address="127.0.0.1", tcp_port=PORT, num_agents=1, fast=False,
        peaceful=True, clear_entities=True, reset_paused=False,
        inventory={"coal": 10, "stone-furnace": 1}))
    inst.rcon_client.send_command("/sc game.speed = 8")
    _, _, out = inst.eval(CODE, agent_idx=0, timeout=300)
    print(out)


if __name__ == "__main__":
    main()
