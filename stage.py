"""Segment (stage) eval runner: N concurrent lanes, one pinned world each.

Divides the run the way speedrunners do (SEGMENTS.md) and tests one segment
as a batch of short concurrent runs: reset the cluster with N instances
(RCON ports 27000..27000+N-1), launch one arena per lane, poll a timeline
every 5s (pinning game.speed=1 so wall time = game time = WR split time),
kill each lane at the tick window, grade against the stage rubric, and
append the results to stage-runs.jsonl.

Usage:
  uv run python stage.py --lane configs/stage1-base-a.json \
      --lane configs/stage1-base-b.json --minutes 5 --label s1-batch1
  uv run python stage.py --grade-only stage-logs/<lane>.timeline.jsonl
Selftest: uv run python stage.py --selftest
"""

import argparse
import json
import os
import subprocess
import threading
import time
from pathlib import Path

HERE = Path(__file__).parent
ENV_PATH = "/Applications/Docker.app/Contents/Resources/bin:" + os.environ["PATH"]
BASE_PORT = 27000
STAGE_RUNS = HERE / "stage-runs.jsonl"
TL_DIR = HERE / "stage-logs"

# One RCON round-trip: pin the requested speed (grading is tick-based, so
# physics-neutral speedup is legal in lab mode — WR-PACE §2/§6), count the
# entities the rubrics care about, read production stats, detect research,
# and read the walking queue (wedge detection). Returns JSON.
POLL_LUA_TMPL = (
    "/sc __PIN__ "
    "local s = game.surfaces[1] "
    "local names = {'burner-mining-drill','stone-furnace','boiler',"
    "'steam-engine','offshore-pump','lab','electric-mining-drill',"
    "'assembling-machine-1','transport-belt','inserter'} "
    "local built = {} "
    "for _, n in pairs(names) do "
    "built[n] = s.count_entities_filtered{name=n, force='player'} end "
    "local pw = 0 "
    "for _, e in pairs(s.find_entities_filtered{name='steam-engine', force='player'}) do "
    "local ok, v = pcall(function() return e.energy_generated_last_tick end) "
    "if ok and v then pw = pw + v end end "
    "local f = game.forces['player'] "
    "local st = f.get_item_production_statistics(s) "
    "local prod = {} "
    "for _, i in pairs({'iron-plate','copper-plate','coal','stone',"
    "'iron-gear-wheel','electronic-circuit'}) do "
    "prod[i] = st.get_input_count(i) end "
    "local total = s.count_entities_filtered{force='player'} "
    "local wq = -1 "
    "local okq, vq = pcall(function() "
    "return fle_actions.get_walking_queue_length(1) end) "
    "if okq then wq = tonumber(vq) or -1 end "
    "local ch = s.find_entities_filtered{name='character'}[1] "
    "local cx, cy = 0, 0 "
    "if ch then cx, cy = ch.position.x, ch.position.y end "
    "rcon.print(helpers.table_to_json({tick=game.tick, built=built, pw=pw, "
    "prod=prod, total=total, wq=wq, cx=cx, cy=cy, "
    "res=(f.current_research and f.current_research.name or '')}))"
)

NUDGE_LUA = (
    "/sc local ch = game.surfaces[1].find_entities_filtered{name='character'}[1] "
    "if ch then local p = ch.position "
    "ch.teleport({p.x + 2, p.y + 2}) rcon.print('nudged') "
    "else rcon.print('no char') end"
)


def poll_lua(speed: float) -> str:
    pin = ("" if not speed else
           f"if game.speed ~= {speed} then game.speed = {speed} end")
    return POLL_LUA_TMPL.replace("__PIN__", pin)


def sh(cmd: str):
    return subprocess.run(cmd, shell=True, cwd=HERE, text=True,
                          capture_output=True,
                          env={**os.environ, "PATH": ENV_PATH})


def rcon(port: int):
    from factorio_rcon import RCONClient
    c = RCONClient("127.0.0.1", port, "factorio")
    c.connect()
    return c


def wait_rcon(port: int, timeout: float = 240) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            c = rcon(port)
            c.send_command("/sc rcon.print(1)")  # also swallows the banner
            c.send_command("/sc rcon.print(1)")
            return True
        except Exception:
            time.sleep(3)
    return False


def start_cluster(n: int, save_file: str | None = None):
    print(f"resetting cluster: {n} instance(s)"
          + (f" from save {save_file}" if save_file else " (pinned scenario)"))
    sh("uv run fle cluster stop")
    if save_file:
        # the CLI doesn't expose save_file; the python API does
        code = ("from fle.cluster.run_envs import start_cluster; "
                f"start_cluster({n}, 'open_world', save_file={save_file!r})")
        r = sh(f"uv run python -c \"{code}\"")
    else:
        r = sh(f"uv run fle cluster start -n {n} -s open_world")
    if r.returncode != 0:
        print(r.stdout[-400:], r.stderr[-400:])
        raise SystemExit("cluster start failed")
    for i in range(n):
        if not wait_rcon(BASE_PORT + i):
            raise SystemExit(f"RCON never came up on port {BASE_PORT + i}")
    print("all instances up")


# ------------------------------------------------------------- grading ------
S1_WINDOW_TICKS = None  # set from --minutes at runtime; 5 min -> 18000

GATE_DEFS = [  # (gate name, fn(sample) -> bool)
    ("first_drill",  lambda d: d["built"].get("burner-mining-drill", 0) > 0),
    ("first_furnace", lambda d: d["built"].get("stone-furnace", 0) > 0),
    ("first_plate",  lambda d: d["prod"].get("iron-plate", 0) > 0),
    ("power_built",  lambda d: d["built"].get("offshore-pump", 0) > 0
        and d["built"].get("boiler", 0) > 0
        and d["built"].get("steam-engine", 0) > 0),
    ("power_gen",    lambda d: d.get("pw", 0) > 0),
    ("lab",          lambda d: d["built"].get("lab", 0) > 0),
    ("research",     lambda d: bool(d.get("res"))),
    ("first_assembler", lambda d: d["built"].get("assembling-machine-1", 0) > 0),
    ("first_belt",   lambda d: d["built"].get("transport-belt", 0) > 0),
    ("electric_drill", lambda d: d["built"].get("electric-mining-drill", 0) > 0),
]


def grade_s1(samples: list, window_ticks: int) -> dict:
    """S1 'Power' rubric (SEGMENTS.md §2): /100.
    power 40 (built 15 + generating 25), drills 30, plates 20, lab+res 10.
    All ticks are RELATIVE to the first sample (the world runs from cluster
    boot; the lane's clock starts when its poller takes sample zero)."""
    t0 = samples[0]["tick"]
    inwin = [d for d in samples if d["tick"] - t0 <= window_ticks] or samples[:1]
    end = inwin[-1]
    gates = {}
    for name, fn in GATE_DEFS:
        hit = next((d for d in samples if fn(d)), None)
        gates[name] = (hit["tick"] - t0) if hit else None

    def in_window(g):
        return gates[g] is not None and gates[g] <= window_ticks

    drills = end["built"].get("burner-mining-drill", 0)
    plates = end["prod"].get("iron-plate", 0)
    # RUBRIC v2 (S1-BIBLE §4): power points require a real economy (>=4
    # drills) — the optimizer found a degenerate 0-drill power-rush that
    # outscored honest play. Power without an economy is a trophy, not a
    # factory.
    economy = drills >= 4
    score = (
        (15 if in_window("power_built") and economy else 0)
        + (25 if in_window("power_gen") and economy else 0)
        + 1.5 * min(drills, 20)
        + min(plates, 150) / 150 * 20
        + (5 if in_window("lab") else 0)
        + (5 if in_window("research") else 0)
    )
    return {
        "score": round(score, 1),
        "gates_min": {k: (round(v / 3600, 2) if v is not None else None)
                      for k, v in gates.items()},
        "end": {"tick": end["tick"] - t0, "drills": drills,
                "furnaces": end["built"].get("stone-furnace", 0),
                "iron_plates": plates,
                "coal": end["prod"].get("coal", 0),
                "entities": end["total"], "power_w_tick": end.get("pw", 0)},
    }


# --------------------------------------------------------------- lanes ------
def run_lane(i: int, cfg_path: str, label: str, minutes: int, results: dict,
             keep_world: bool, speed: float = 1.0, tag: str = "lab",
             reuse: bool = False):
    port = BASE_PORT + i
    stem = Path(cfg_path).stem
    lane_label = f"{label}:L{i}:{stem}"
    # rotate the lane's agent ledgers so per-run analysis is clean
    cfg = json.loads((HERE / cfg_path).read_text())
    for a in cfg["agents"]:
        slug = a["name"].replace(" ", "_").lower()
        f = HERE / "arena-logs" / f"{slug}.jsonl"
        if f.exists():
            f.rename(HERE / "arena-logs" / f"{slug}.{int(time.time())}.old")
    tl_path = TL_DIR / f"{label}_L{i}_{stem}.timeline.jsonl"
    log_path = TL_DIR / f"{label}_L{i}_{stem}.arena.log"
    env = {**os.environ, "PATH": ENV_PATH, "FLE_SPECTATOR_MODE": "1",
           "ARENA_CONFIG": cfg_path, "ARENA_RCON_PORT": str(port),
           "ARENA_NO_RENDER": "1", "RUN_LABEL": lane_label}
    if keep_world:
        env["ARENA_KEEP_WORLD"] = "1"
    proc = subprocess.Popen(["uv", "run", "python", "arena.py"], cwd=HERE,
                            stdout=open(log_path, "w"),
                            stderr=subprocess.STDOUT, env=env)
    window_ticks = minutes * 3600
    samples = []
    c = None
    lua = poll_lua(speed)
    wall_budget = minutes * 60 * 2.5 + 180 if speed <= 1 else \
        minutes * 60 / max(speed, 1) * 4 + 240
    hard_deadline = time.time() + wall_budget
    last_nudge = 0.0
    # cluster-reuse rounds: sample zero must land AFTER arena wipes the
    # previous round's world (clear_entities also zeroes production stats) —
    # otherwise gates fire at 0.0 min against leftover bases and prod deltas
    # go negative (route-search g2/g3 contamination bug).
    started = not reuse
    t_open = time.time()
    with open(tl_path, "w") as tf:
        while time.time() < hard_deadline:
            try:
                if c is None:
                    c = rcon(port)
                d = json.loads(c.send_command(lua))
            except Exception:
                c = None
                time.sleep(3)
                continue
            if not started:
                if d.get("total", 99) <= 2 or time.time() - t_open > 150:
                    started = True
                    tf.write(json.dumps({"wipe_anchor": d.get("total"),
                                         "t": round(time.time(), 1)}) + "\n")
                else:
                    time.sleep(2)
                    continue
            d["t"] = round(time.time(), 1)
            samples.append(d)
            tf.write(json.dumps(d) + "\n")
            tf.flush()
            if d["tick"] - samples[0]["tick"] >= window_ticks:
                break
            # wedge watchdog (lab mode only): walking queue stuck non-empty
            # and character not moving across 3 samples -> 2-tile nudge,
            # logged. A stuck FLE pathfinder is a harness bug (WR-PACE §4).
            if (tag == "lab" and len(samples) >= 3
                    and time.time() - last_nudge > 30):
                w = [(s.get("wq", -1), s.get("cx"), s.get("cy"))
                     for s in samples[-3:]]
                if (w[0][0] > 0 and len({x[0] for x in w}) == 1
                        and len({(x[1], x[2]) for x in w}) == 1):
                    try:
                        r = c.send_command(NUDGE_LUA)
                        last_nudge = time.time()
                        tf.write(json.dumps({"nudge": r,
                                             "t": round(time.time(), 1)}) + "\n")
                        tf.flush()
                    except Exception:
                        pass
            time.sleep(5 if speed <= 1 else 2)
    proc.terminate()
    time.sleep(3)
    if proc.poll() is None:
        proc.kill()
    if not samples:
        results[i] = {"lane": lane_label, "error": "no samples"}
        return
    # normalize production stats to the first sample: the Lua counters are
    # per-force cumulative and survive cluster-reuse rounds
    p0 = samples[0].get("prod", {})
    for d in samples:
        d["prod"] = {k: v - p0.get(k, 0) for k, v in d.get("prod", {}).items()}
    g = grade_s1(samples, window_ticks)
    results[i] = {"ts": time.time(), "lane": lane_label, "config": cfg_path,
                  "minutes": minutes, "tag": tag, "speed": speed, **g}
    with open(STAGE_RUNS, "a") as f:
        f.write(json.dumps(results[i]) + "\n")


def verdict(results: dict):
    print("\n===== STAGE VERDICT =====")
    for i in sorted(results):
        r = results[i]
        if "error" in r:
            print(f"L{i} {r['lane']}: ERROR {r['error']}")
            continue
        e, gm = r["end"], r["gates_min"]
        gtxt = " ".join(f"{k}={gm[k]}" for k in
                        ("first_drill", "first_plate", "power_built",
                         "power_gen", "lab") if gm.get(k) is not None)
        print(f"L{i} {Path(r['config']).stem:<22} score={r['score']:>5} "
              f"drills={e['drills']:>2} furn={e['furnaces']:>2} "
              f"plates={e['iron_plates']:>4} ents={e['entities']:>3} "
              f"| gates(min): {gtxt or 'none'}")


def preflight_accounts(lane_cfgs: list):
    """Probe every account pool with a 1-line haiku call; a lane whose pools
    are ALL rate-limited runs brainless (s1-batch1: 2 of 4 lanes dead on
    weekly-limited accounts). Abort in that case."""
    accts = {}
    for cfg_path in lane_cfgs:
        cfg = json.loads((HERE / cfg_path).read_text())
        for a in cfg["agents"]:
            if a.get("script_only") or not a.get("accounts"):
                continue  # brainless route lanes need no pool
            for acct in a["accounts"]:
                accts.setdefault(acct, None)
    if not accts:
        print("  (all lanes script-only — no account preflight needed)")
        return

    def probe(acct):
        env = {k: v for k, v in os.environ.items()
               if k != "ANTHROPIC_API_KEY" and k != "CLAUDECODE"
               and not k.startswith("CLAUDE_CODE_")}
        env["CLAUDE_CONFIG_DIR"] = os.path.expanduser(acct)
        try:
            out = subprocess.run(
                ["claude", "-p", "reply with the word ok", "--model", "haiku",
                 "--output-format", "json", "--max-turns", "2"],
                capture_output=True, text=True, env=env, timeout=90)
            res = json.loads(out.stdout).get("result", "")
            accts[acct] = "ok" if out.returncode == 0 else f"DEAD: {res[:60]}"
        except Exception as e:
            accts[acct] = f"DEAD: {str(e)[:60]}"

    ts = [threading.Thread(target=probe, args=(a,)) for a in accts]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    for a, st in accts.items():
        print(f"  account {Path(a).name}: {st}")
    for cfg_path in lane_cfgs:
        cfg = json.loads((HERE / cfg_path).read_text())
        for a in cfg["agents"]:
            if a.get("script_only") or not a.get("accounts"):
                continue
            if not any(accts[x] == "ok" for x in a["accounts"]):
                raise SystemExit(
                    f"lane {cfg_path}: all account pools dead — fix accounts")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", action="append", required=True,
                    help="config json per concurrent lane (repeatable)")
    ap.add_argument("--minutes", type=int, default=5)
    ap.add_argument("--label", default=time.strftime("stage-%m%d-%H%M"))
    ap.add_argument("--save", default=None,
                    help="boot every instance from this save (stage relay)")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="pin game.speed (0 = leave unpinned). Lab-mode "
                         "physics-neutral speedup; grading is tick-based")
    ap.add_argument("--tag", default="lab", choices=["lab", "match"],
                    help="run class — lab numbers never compare to match")
    ap.add_argument("--no-cluster-reset", action="store_true",
                    help="reuse running instances (FLE clear_entities still "
                         "wipes builds per lane; prod stats delta-normalized)")
    args = ap.parse_args()
    TL_DIR.mkdir(exist_ok=True)
    print("preflighting account pools…")
    preflight_accounts(args.lane)
    reuse = args.no_cluster_reset and all(
        wait_rcon(BASE_PORT + i, timeout=5) for i in range(len(args.lane)))
    if reuse:
        print(f"reusing running cluster ({len(args.lane)} instances)")
    else:
        start_cluster(len(args.lane), args.save)
    results = {}
    threads = [threading.Thread(target=run_lane,
                                args=(i, cfg, args.label, args.minutes,
                                      results, bool(args.save),
                                      args.speed, args.tag, reuse),
                                name=f"lane-{i}")
               for i, cfg in enumerate(args.lane)]
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    verdict(results)


def selftest():
    fake = [
        {"tick": 600, "built": {}, "prod": {}, "pw": 0, "total": 0, "res": ""},
        {"tick": 9000, "built": {"burner-mining-drill": 4, "stone-furnace": 4},
         "prod": {"iron-plate": 40}, "pw": 0, "total": 9, "res": ""},
        {"tick": 17500, "built": {"burner-mining-drill": 8, "stone-furnace": 8,
                                  "offshore-pump": 1, "boiler": 1,
                                  "steam-engine": 2},
         "prod": {"iron-plate": 120, "coal": 80}, "pw": 900, "total": 21,
         "res": "automation"},
    ]
    g = grade_s1(fake, 18000)
    assert g["gates_min"]["first_drill"] == 2.33, g   # (9000-600)/3600
    assert g["gates_min"]["power_gen"] == 4.69, g     # (17500-600)/3600
    # 15 + 25 + 12 + 16 + 0 + 5 = 73
    assert g["score"] == 73.0, g
    assert g["end"]["drills"] == 8
    print("selftest OK:", json.dumps(g))


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        selftest()
    elif "--grade-only" in sys.argv:
        p = sys.argv[sys.argv.index("--grade-only") + 1]
        samples = [json.loads(l) for l in open(p)]
        print(json.dumps(grade_s1(samples, 18000), indent=2))
    else:
        main()
