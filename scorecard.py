"""Run scorecard: snapshot world/production state into runs.jsonl and compare.

Usage:
  uv run python scorecard.py snapshot --label solo-opus-1 [--note "..."]
  uv run python scorecard.py report            # table across all runs
  uv run python scorecard.py fingerprint       # map determinism check
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

from factorio_rcon import RCONClient

HERE = Path(__file__).parent
RUNS = HERE / "runs.jsonl"

KEY_ITEMS = ["iron-plate", "copper-plate", "steel-plate", "iron-gear-wheel",
             "electronic-circuit", "transport-belt", "inserter",
             "automation-science-pack", "logistic-science-pack"]

TIER_ENTITIES = [  # (tier name, entity that proves it)
    ("burner-mining", "burner-mining-drill"),
    ("smelting", "stone-furnace"),
    ("power", "steam-engine"),
    ("electric-mining", "electric-mining-drill"),
    ("science", "lab"),
    ("automation", "assembling-machine-1"),
    ("logistics", "transport-belt"),
]


def rcon():
    c = RCONClient("127.0.0.1", 27000, "factorio")
    c.connect()
    return c


def world_state(c):
    raw = c.send_command((
        "/sc local built = {} "
        "for _, e in pairs(game.surfaces[1].find_entities_filtered{force='player'}) do "
        "if e.name ~= 'character' then built[e.name] = (built[e.name] or 0) + 1 end end "
        "local f = game.forces['player'] "
        "local stats = f.get_item_production_statistics(game.surfaces[1]) "
        "local prod = {} "
        + " ".join(f"prod['{i}'] = stats.get_input_count('{i}')" for i in KEY_ITEMS)
        + " rcon.print(helpers.table_to_json({built=built, prod=prod, tick=game.tick}))"
    ))
    d = json.loads(raw)
    if not isinstance(d.get("built"), dict):
        d["built"] = {}
    return d


def snapshot(label, note=""):
    c = rcon()
    d = world_state(c)
    built = d["built"]
    tiers = [name for name, ent in TIER_ENTITIES if built.get(ent)]
    try:
        from arena import AGENTS, MIN_STEP_S, STEPS
        config = {"agents": [{k: a[k] for k in ("name", "brain", "model")} for a in AGENTS],
                  "pacing_s": MIN_STEP_S, "steps": STEPS}
    except Exception:
        config = {}
    entry = {
        "ts": time.time(), "label": label, "note": note,
        "tick": d["tick"], "built": built,
        "entities_total": sum(built.values()),
        "produced": d["prod"], "tiers": tiers,
        "config": config,
    }
    with open(RUNS, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry, indent=2))
    return entry


def report():
    if not RUNS.exists():
        print("no runs yet")
        return
    rows = [json.loads(l) for l in open(RUNS)]
    cols = ["label", "entities", "iron", "gears", "circuits", "red-sci", "top tier"]
    print(" | ".join(f"{c:>14}" for c in cols))
    print("-" * (17 * len(cols)))
    for r in rows:
        p = r["produced"]
        print(" | ".join(f"{str(v):>14}" for v in [
            r["label"][:14], r["entities_total"], p.get("iron-plate", 0),
            p.get("iron-gear-wheel", 0), p.get("electronic-circuit", 0),
            p.get("automation-science-pack", 0),
            (r["tiers"][-1] if r["tiers"] else "-"),
        ]))


def fingerprint():
    """Hash the natural resources near origin — identical across boots iff
    the map seed pin is working."""
    c = rcon()
    raw = c.send_command(
        "/sc local t = {} "
        "for _, e in pairs(game.surfaces[1].find_entities_filtered{type='resource', "
        "area={{-80,-80},{80,80}}}) do "
        "table.insert(t, e.name .. ':' .. e.position.x .. ',' .. e.position.y) end "
        "table.sort(t) rcon.print(#t .. '|' .. table.concat(t, ';'))")
    n, _, body = raw.partition("|")
    h = hashlib.sha256(body.encode()).hexdigest()[:16]
    print(f"resources near origin: {n}  fingerprint: {h}")
    return h


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--label", required=True)
    s.add_argument("--note", default="")
    sub.add_parser("report")
    sub.add_parser("fingerprint")
    args = ap.parse_args()
    if args.cmd == "snapshot":
        snapshot(args.label, args.note)
    elif args.cmd == "report":
        report()
    else:
        fingerprint()
