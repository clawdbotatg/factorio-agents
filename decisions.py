"""Per-decision ledger: what did each step buy?

Usage:
  uv run python decisions.py <agent-slug>     # e.g. factory_one
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent

PHASE_MARKS = [  # (phase, substring that proves the decision entered it)
    ("first-drill", "burner-mining-drill"),
    ("power", "steam-engine"),
    ("electric-drill", "electric-mining-drill"),
    ("assembler", "assembling-machine"),
    ("belts", "transport-belt"),
    ("science", "automation-science-pack"),
]


def main(slug: str):
    path = HERE / "arena-logs" / f"{slug}.jsonl"
    events = [json.loads(l) for l in open(path)]

    # stitch steps: thought -> code -> score
    steps, cur = [], {}
    for e in events:
        if e["kind"] == "thought":
            cur = {"thought": e["text"].strip().split("\n")[0][:90], "ts": e["ts"]}
        elif e["kind"] == "code":
            cur["code"] = e["text"]
        elif e["kind"] == "score":
            m = json.loads(e["text"])
            cur.update(m)
            steps.append(cur)
            cur = {}

    if not steps:
        print("no scored steps yet (score events start with the ledger-enabled runs)")
        return

    t0 = steps[0]["ts"]
    prev_score, prev_ent = 0, 0
    gates, waste_run, wasted = {}, 0, 0
    print(f"{'step':>4} {'min':>5} {'Δscore':>8} {'Δent':>5}  decision")
    print("-" * 100)
    for s in steps:
        ds = (s.get("score") or 0) - prev_score
        de = (s.get("entities") or prev_ent) - prev_ent
        prev_score = s.get("score") or prev_score
        prev_ent = s.get("entities") or prev_ent
        flag = ""
        if ds <= 0 and de <= 0:
            waste_run += 1
            wasted += 1
            if waste_run >= 3:
                flag = "  ⚠ stall"
        else:
            waste_run = 0
        for phase, mark in PHASE_MARKS:
            if phase not in gates and mark in s.get("code", ""):
                gates[phase] = (s["ts"] - t0) / 60
                flag += f"  ★ {phase}"
        print(f"{s['step']:>4} {(s['ts']-t0)/60:>5.1f} {ds:>8.0f} {de:>5} "
              f" {s.get('thought','')[:70]}{flag}")

    n = len(steps)
    print("-" * 100)
    print(f"steps: {n} | zero-gain steps: {wasted} ({100*wasted//max(n,1)}%) "
          f"| final score: {prev_score:.0f} | entities: {prev_ent}")
    print("phase gates (minutes):",
          {k: round(v, 1) for k, v in gates.items()} or "none hit")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "factory_one")
