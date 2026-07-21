"""Evolutionary S1 route search — no LLM anywhere (WR-PACE §1/§2).

Population of skill-plan candidates evaluated as 10 concurrent script-only
lanes per generation at pinned lab speed (physics-neutral). Elitism +
mutation; the champion is re-evaluated every generation so its fitness is a
running median, not a lucky roll. Results: route-champions.jsonl, full grades
in stage-runs.jsonl (label route-g<N>, tag lab).

Usage:
  uv run python route_search.py --hours 8 --speed 4
"""

import argparse
import copy
import json
import random
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).parent
RDIR = HERE / "configs" / "route"
CHAMPS = HERE / "route-champions.jsonl"

# Kit-aware match-physics seed: the vanilla starting kit (1 drill, 1
# furnace, 8 plates) means the FIRST move is fueling and placing the free
# drill — the WR opening — not hand-mining an economy from nothing.
SEED_PLAN = [
    {"skill": "gather", "args": {"coal": 12}},
    {"skill": "mine_line", "args": {"resource": "iron", "n": 1}},
    {"skill": "gather", "args": {"iron": 20, "stone": 8}},
    {"skill": "keep_fed", "args": {}},
    {"skill": "bootstrap_place", "args": {}},
    {"skill": "bootstrap_feed", "args": {}},
    {"skill": "keep_fed", "args": {}},
    {"skill": "mine_line", "args": {"resource": "iron", "n": 2}},
    {"skill": "mine_line", "args": {"resource": "coal", "n": 1}},
    {"skill": "keep_fed", "args": {}},
    {"skill": "power_craft", "args": {}},
    {"skill": "power_build", "args": {}},
    {"skill": "mine_line", "args": {"resource": "copper", "n": 2}},
    {"skill": "keep_fed", "args": {}},
    {"skill": "mine_line", "args": {"resource": "iron", "n": 6}},
    {"skill": "keep_fed", "args": {}},
    {"skill": "lab", "args": {}},
    {"skill": "research", "args": {}},
]

VOCAB = [
    lambda: {"skill": "gather", "args": {"iron": random.choice([10, 18, 24])}},
    lambda: {"skill": "gather", "args": {"coal": random.choice([8, 15, 20])}},
    lambda: {"skill": "gather", "args": {"stone": random.choice([8, 14, 20])}},
    lambda: {"skill": "mine_line", "args": {"resource": "iron",
                                            "n": random.randint(2, 6)}},
    lambda: {"skill": "mine_line", "args": {"resource": "coal",
                                            "n": random.randint(1, 4)}},
    lambda: {"skill": "mine_line", "args": {"resource": "stone",
                                            "n": random.randint(1, 2)}},
    lambda: {"skill": "mine_line", "args": {"resource": "copper",
                                            "n": random.randint(1, 3)}},
    lambda: {"skill": "keep_fed", "args": {}},
    lambda: {"skill": "expand_smelting", "args": {"n": random.randint(2, 6)}},
    lambda: {"skill": "power_craft", "args": {}},
    lambda: {"skill": "power_build", "args": {}},
    lambda: {"skill": "bootstrap_feed", "args": {}},
    lambda: {"skill": "lab", "args": {}},
    lambda: {"skill": "research", "args": {}},
]


def mutate(plan):
    p = copy.deepcopy(plan)
    op = random.random()
    if op < 0.3 and len(p) > 4:                      # tweak a number
        for _ in range(10):
            it = random.choice(p)
            if it["skill"] == "mine_line":
                it["args"]["n"] = max(1, it["args"].get("n", 2)
                                      + random.choice([-2, -1, 1, 2]))
                break
            if it["skill"] == "gather" and it["args"]:
                k = random.choice(list(it["args"]))
                it["args"][k] = max(5, it["args"][k] + random.choice([-10, 10]))
                break
    elif op < 0.55 and len(p) > 3:                   # swap adjacent
        i = random.randrange(len(p) - 1)
        p[i], p[i + 1] = p[i + 1], p[i]
    elif op < 0.8:                                   # insert
        p.insert(random.randrange(len(p) + 1), random.choice(VOCAB)())
    elif len(p) > 5:                                 # delete
        i = random.randrange(len(p))
        if p[i]["skill"] not in ("bootstrap_place",):
            p.pop(i)
    return p


def write_configs(pop, gen, speed=4.0):
    RDIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, plan in enumerate(pop):
        cfg = {"agents": [{
            "name": f"Route G{gen} C{i}",
            "mode": "skills", "script_only": True,
            "model": "none", "accounts": [],
            "timeout_cap": 90, "default_plan": plan,
            "wall_sleep_scale": round(1.0 / max(speed, 1), 3),
        }], "fast": False, "steps": 400,
            "shared_goal": "scripted route eval — no brain"}
        path = RDIR / f"cand-{i}.json"
        path.write_text(json.dumps(cfg, indent=1))
        paths.append(str(path.relative_to(HERE)))
    return paths


SEED_POOL = json.load(open(HERE / "seed-pool.json"))


def eval_generation(paths, gen, speed, full_reset):
    label = f"route-g{gen}"
    import os
    # rotate the lab seed pool on every full reset: anything that only wins
    # on one map should die in the lab (first live match proved it)
    os.environ["FLE_SEED"] = str(SEED_POOL[(gen // 6) % len(SEED_POOL)])
    os.environ["FLE_SPACE_AGE"] = "1"
    cmd = ["uv", "run", "python", "stage.py", "--minutes", "5",
           "--speed", str(speed), "--tag", "lab", "--label", label]
    if not full_reset:
        cmd.append("--no-cluster-reset")
    for p in paths:
        cmd += ["--lane", p]
    subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                   timeout=3600)
    rows = [json.loads(l) for l in open(HERE / "stage-runs.jsonl")]
    out = {}
    for r in rows:
        if r.get("lane", "").startswith(label + ":") and "score" in r:
            i = int(r["lane"].split(":L")[1].split(":")[0])
            out[i] = r["score"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=8)
    ap.add_argument("--speed", type=float, default=4)
    ap.add_argument("--pop", type=int, default=10)
    args = ap.parse_args()
    deadline = time.time() + args.hours * 3600

    champion = copy.deepcopy(SEED_PLAN)
    champ_scores = []
    survivors = [copy.deepcopy(SEED_PLAN)]
    gen = 0
    force_reset = False
    while time.time() < deadline:
        gen += 1
        pop = [copy.deepcopy(champion)]
        pop += [copy.deepcopy(s) for s in survivors[:2]]
        while len(pop) < args.pop:
            pop.append(mutate(random.choice([champion] + survivors[:2])))
        paths = write_configs(pop, gen, args.speed)
        try:
            scores = eval_generation(paths, gen, args.speed,
                                     full_reset=(gen % 6 == 1 or force_reset))
        except Exception as e:
            print(f"g{gen}: eval error {str(e)[:120]} — full reset next")
            force_reset = True
            continue
        # a partially-graded generation means sick lanes/instances — recover
        force_reset = len(scores) < args.pop * 0.7
        if force_reset:
            print(f"g{gen}: only {len(scores)}/{args.pop} graded — "
                  "full cluster reset next generation")
        if not scores:
            continue
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        champ_scores.append(scores.get(0, 0))
        champ_med = sorted(champ_scores[-7:])[len(champ_scores[-7:]) // 2]
        best_i, best_s = ranked[0]
        print(f"g{gen}: best={best_s} (cand {best_i}) champ_med={champ_med} "
              f"scores={dict(ranked)}")
        # promotion: a mutant must beat the champion's running median +2
        if best_i != 0 and best_s > champ_med + 2:
            champion = pop[best_i]
            champ_scores = [best_s]
            print(f"g{gen}: NEW CHAMPION (score {best_s})")
        survivors = [pop[i] for i, _ in ranked[:3] if i != 0][:2] or [champion]
        with open(CHAMPS, "a") as f:
            f.write(json.dumps({"gen": gen, "ts": time.time(),
                                "best_score": best_s,
                                "champ_median": champ_med,
                                "champion": champion}) + "\n")
    print("route search done —", gen, "generations")


if __name__ == "__main__":
    main()
