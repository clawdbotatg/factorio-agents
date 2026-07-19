"""A/B experiment runner: two configs, same pinned map, same clock, verdict.

Usage:
  uv run python experiment.py --a configs/solo-sonnet.json \
      --b configs/solo-opus.json --minutes 45 [--label sonnet-vs-opus]

Each side: fresh world (pinned seed) -> arena under that config -> run for
--minutes -> stop -> scorecard snapshot. Ends with a comparison table.
"""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).parent
ENV_PATH = "/Applications/Docker.app/Contents/Resources/bin:" + os.environ["PATH"]


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, cwd=HERE, text=True,
                          capture_output=True,
                          env={**os.environ, "PATH": ENV_PATH}, **kw)


def fresh_world():
    print("  resetting world (pinned seed)…")
    sh("uv run fle cluster stop")
    r = sh("uv run fle cluster start -n 1 -s open_world")
    if "Started" not in r.stdout + r.stderr and "started" not in (r.stdout + r.stderr):
        print(r.stdout[-300:], r.stderr[-300:])
    time.sleep(12)


def run_side(side: str, config: str, minutes: int, label: str):
    run_label = f"{label}:{side}"
    print(f"[{side}] {config} for {minutes}min → label {run_label}")
    fresh_world()
    # clear the agent logs this run will use, so decisions.py is per-run
    cfg = json.loads((HERE / config).read_text())
    slugs = [a["name"].replace(" ", "_").lower() for a in cfg["agents"]]
    for slug in slugs:
        f = HERE / "arena-logs" / f"{slug}.jsonl"
        if f.exists():
            f.rename(HERE / "arena-logs" / f"{slug}.{int(time.time())}.old")
    proc = subprocess.Popen(
        ["uv", "run", "python", "arena.py"], cwd=HERE,
        stdout=open(HERE / f"arena-{side}.log", "w"), stderr=subprocess.STDOUT,
        env={**os.environ, "PATH": ENV_PATH, "FLE_SPECTATOR_MODE": "1",
             "ARENA_CONFIG": config, "RUN_LABEL": run_label},
    )
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        if proc.poll() is not None:
            print(f"  arena exited early (rc={proc.returncode})")
            break
        time.sleep(20)
    if proc.poll() is None:
        proc.terminate()
        time.sleep(3)
        if proc.poll() is None:
            proc.kill()
    sh(f"uv run python scorecard.py snapshot --label '{run_label}:end'")
    for slug in slugs:
        print(f"  --- decision summary: {slug}")
        r = sh(f"uv run python decisions.py {slug}")
        print("\n".join(r.stdout.splitlines()[-4:]))
    return run_label


def compare(label):
    rows = [json.loads(l) for l in open(HERE / "runs.jsonl")]
    ends = {r["label"]: r for r in rows if r["label"].startswith(label)
            and r["label"].endswith(":end")}
    print("\n===== VERDICT =====")
    for name, r in ends.items():
        p = r["produced"]
        print(f"{name}: entities={r['entities_total']} iron={p.get('iron-plate',0)} "
              f"gears={p.get('iron-gear-wheel',0)} circuits={p.get('electronic-circuit',0)} "
              f"red-sci={p.get('automation-science-pack',0)} top-tier={r['tiers'][-1] if r['tiers'] else '-'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--vs", help="single live head-to-head run with this config")
    ap.add_argument("--minutes", type=int, default=45)
    ap.add_argument("--label", default=None)
    args = ap.parse_args()
    label = args.label or f"exp-{time.strftime('%m%d-%H%M')}"
    if args.vs:
        run_side("VS", args.vs, args.minutes, label)
        print("\n===== FINAL TERRITORY SCORE =====")
        r = sh("uv run python scorecard.py vs")
        print(r.stdout)
    else:
        assert args.a and args.b, "need --a and --b (or --vs)"
        run_side("A", args.a, args.minutes, label)
        run_side("B", args.b, args.minutes, label)
        compare(label)
    print("\ndone — full table: uv run python scorecard.py report")
