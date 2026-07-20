"""Measure the wall-clock cost of legal-mode primitives on this box.

Times each FLE primitive at fast=False (walk, harvest, craft, place, insert)
against the live cluster. This is the budget every stage skill must be sized
against — and the fairness check against WR splits (a real character walks
~2.5 tiles/s; if FLE legal walking is much slower, our stage windows must be
rescaled).

Usage: uv run python probe_legal.py [port]
"""

import asyncio
import os
import sys
import time

os.environ.setdefault("FLE_SPECTATOR_MODE", "1")

from fle.env.a2a_instance import A2AFactorioInstance  # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 27000


def timed(inst, label, code, timeout=240):
    t0 = time.time()
    try:
        _, _, out = inst.eval(code, agent_idx=0, timeout=timeout)
    except Exception as e:
        out = f"EVAL ERROR: {e}"
    dt = time.time() - t0
    print(f"{dt:7.1f}s  {label}\n         -> {str(out)[:200]}")
    return dt


def main():
    inst = asyncio.run(A2AFactorioInstance.create(
        address="127.0.0.1", tcp_port=PORT, num_agents=1, fast=False,
        peaceful=True, clear_entities=True, reset_paused=False))
    print("instance ready (legal mode)")
    timed(inst, "observe: position + nearest patches",
          "p = player_location if 'player_location' in dir() else None\n"
          "print('iron', nearest(Resource.IronOre))\n"
          "print('coal', nearest(Resource.Coal))\n"
          "print('stone', nearest(Resource.Stone))\n"
          "print('water', nearest(Resource.Water))")
    timed(inst, "walk to iron patch",
          "ip = nearest(Resource.IronOre)\nmove_to(ip)\nprint('at', ip)")
    timed(inst, "harvest 10 iron ore (at patch)",
          "harvest_resource(nearest(Resource.IronOre), 10)\n"
          "print(inspect_inventory())")
    timed(inst, "harvest 30 more iron ore",
          "harvest_resource(nearest(Resource.IronOre), 30)\n"
          "print(inspect_inventory())")
    timed(inst, "walk to stone + harvest 12",
          "sp = nearest(Resource.Stone)\nmove_to(sp)\n"
          "harvest_resource(sp, 12)\nprint(inspect_inventory())")
    timed(inst, "craft 2 stone furnaces",
          "craft_item(Prototype.StoneFurnace, 2)\nprint(inspect_inventory())")
    timed(inst, "walk back to iron + place furnace",
          "ip = nearest(Resource.IronOre)\nmove_to(ip)\n"
          "f = place_entity(Prototype.StoneFurnace, "
          "position=Position(x=ip.x+2, y=ip.y-2))\nprint('placed', f.position)")
    timed(inst, "walk to coal + harvest 15",
          "cp = nearest(Resource.Coal)\nmove_to(cp)\n"
          "harvest_resource(cp, 15)\nprint(inspect_inventory())")
    timed(inst, "walk back + insert coal+ore into furnace",
          "ents = get_entities(radius=200)\n"
          "f = [e for e in ents if e.name == 'stone-furnace'][0]\n"
          "move_to(f.position)\n"
          "insert_item(Prototype.Coal, f, quantity=5)\n"
          "insert_item(Prototype.IronOre, f, quantity=10)\n"
          "print('fed')")
    timed(inst, "sleep(10) game-seconds", "sleep(10)\nprint('slept')")
    timed(inst, "extract plates",
          "ents = get_entities(radius=200)\n"
          "f = [e for e in ents if e.name == 'stone-furnace'][0]\n"
          "move_to(f.position)\n"
          "got = extract_item(Prototype.IronPlate, f, quantity=10)\n"
          "print('got', got)")


if __name__ == "__main__":
    main()
