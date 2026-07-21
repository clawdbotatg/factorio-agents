"""Regenerate S1-BIBLE.md's empirical tables from stage-runs.jsonl.

Splits rows into physics eras (the harvest throttle landed f35a801,
2026-07-20 ~22:44 MDT) and prints markdown payoff tables: score by drill
count, power/no-power, early/late first drill, and the current top routes.
Read-only; paste the output into S1-BIBLE.md §4 when it shifts.

Usage: uv run python bible_stats.py [--since-ts TS]
"""

import argparse
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).parent
MATCH_TS = 1784608000  # first clean match-physics route-search rows


def med(xs):
    return round(st.median(xs), 1) if xs else None


def table(rows, title):
    print(f"\n### {title} (n={len(rows)})\n")
    if not rows:
        return
    print("| drills at end | n | median score | median plates | median first_drill (min) |")
    print("|---|---|---|---|---|")
    byd = {}
    for r in rows:
        byd.setdefault(min(r["end"]["drills"], 10), []).append(r)
    for k in sorted(byd):
        b = byd[k]
        fd = [x["gates_min"]["first_drill"] for x in b
              if x["gates_min"]["first_drill"]]
        print(f"| {k} | {len(b)} | {med([x['score'] for x in b])} "
              f"| {med([x['end']['iron_plates'] for x in b])} "
              f"| {med(fd) or '—'} |")
    pb = [r["score"] for r in rows if r["gates_min"]["power_built"] is not None]
    npb = [r["score"] for r in rows if r["gates_min"]["power_built"] is None]
    print(f"\npower built: n={len(pb)} median {med(pb)} | "
          f"no power: n={len(npb)} median {med(npb)}")
    fd = sorted((r["gates_min"]["first_drill"], r["score"]) for r in rows
                if r["gates_min"]["first_drill"])
    if len(fd) > 7:
        h = len(fd) // 2
        print(f"first_drill ≤{fd[h][0]}m: median {med([x[1] for x in fd[:h]])}"
              f" | later: median {med([x[1] for x in fd[h:]])}")
    best = sorted(rows, key=lambda r: -r["score"])[:5]
    print("\ntop lanes:")
    for r in best:
        g = r["gates_min"]
        print(f"- {r['lane']}: {r['score']} (drills {r['end']['drills']}, "
              f"plates {r['end']['iron_plates']}, power {g['power_built']}, "
              f"lab {g['lab']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-ts", type=float, default=0)
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(HERE / "stage-runs.jsonl")]
    rows = [r for r in rows if "score" in r and r["ts"] >= args.since_ts]
    cheat, match = [], []
    for r in rows:
        # match era = route-search rows after the throttle landed; everything
        # else (including contaminated pre-fix route rows) is cheat-era
        if r["lane"].startswith("route-g") and r["ts"] > MATCH_TS:
            match.append(r)
        else:
            cheat.append(r)
    table(cheat, "Cheat-era (pre-throttle — ranks strategies, not routes)")
    table(match, "Match-physics era (vanilla harvest rate)")


if __name__ == "__main__":
    main()
