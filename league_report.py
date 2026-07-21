"""Aggregate stage-runs.jsonl by variant: median/range per config kind.

Usage: uv run python league_report.py [label-prefix]   (default: s1-wide)
"""

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).parent
prefix = sys.argv[1] if len(sys.argv) > 1 else "s1-wide"

rows = [json.loads(l) for l in open(HERE / "stage-runs.jsonl")]
rows = [r for r in rows if r.get("lane", "").startswith(prefix) and "score" in r]

by_kind = {}
for r in rows:
    stem = Path(r["config"]).stem            # stage1-w04-pace
    kind = stem.split("-")[-1]               # base | pace | powerpack
    by_kind.setdefault(kind, []).append(r)

print(f"{'variant':<12} {'n':>3} {'median':>7} {'mean':>6} {'min':>5} {'max':>5} "
      f"{'power%':>7} {'drills(med)':>11}")
for kind, rs in sorted(by_kind.items()):
    scores = [r["score"] for r in rs]
    powered = sum(1 for r in rs if r["gates_min"].get("power_built") is not None)
    drills = [r["end"]["drills"] for r in rs]
    print(f"{kind:<12} {len(rs):>3} {statistics.median(scores):>7.1f} "
          f"{statistics.mean(scores):>6.1f} {min(scores):>5.1f} {max(scores):>5.1f} "
          f"{100 * powered // len(rs):>6}% {statistics.median(drills):>11.1f}")

print("\nper-round detail:")
for r in rows:
    print(f"  {r['lane']:<38} score={r['score']:>5}  "
          f"power={r['gates_min'].get('power_built')}  "
          f"drills={r['end']['drills']}")
