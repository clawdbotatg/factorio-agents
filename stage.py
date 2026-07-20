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

# One RCON round-trip: pin speed 1, count the entities the rubrics care
# about, read production stats, detect research. Returns JSON.
POLL_LUA = (
    "/sc if game.speed ~= 1 then game.speed = 1 end "
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
    "rcon.print(helpers.table_to_json({tick=game.tick, built=built, pw=pw, "
    "prod=prod, total=total, "
    "res=(f.current_research and f.current_research.name or '')}))"
)


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
    score = (
        (15 if in_window("power_built") else 0)
        + (25 if in_window("power_gen") else 0)
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
             keep_world: bool):
    port = BASE_PORT + i
    stem = Path(cfg_path).stem
    lane_label = f"{label}:L{i}:{stem}"
    tl_path = TL_DIR / f"{label}_L{i}_{stem}.timeline.jsonl"
    log_path = TL_DIR / f"{label}_L{i}_{stem}.arena.log"
    env = {**os.environ, "PATH": ENV_PATH, "FLE_SPECTATOR_MODE": "1",
           "ARENA_CONFIG": cfg_path, "ARENA_RCON_PORT": str(port),
           "RUN_LABEL": lane_label}
    if keep_world:
        env["ARENA_KEEP_WORLD"] = "1"
    proc = subprocess.Popen(["uv", "run", "python", "arena.py"], cwd=HERE,
                            stdout=open(log_path, "w"),
                            stderr=subprocess.STDOUT, env=env)
    window_ticks = minutes * 3600
    samples = []
    c = None
    hard_deadline = time.time() + minutes * 60 * 2.5 + 180
    with open(tl_path, "w") as tf:
        while time.time() < hard_deadline:
            try:
                if c is None:
                    c = rcon(port)
                d = json.loads(c.send_command(POLL_LUA))
            except Exception:
                c = None
                time.sleep(3)
                continue
            d["t"] = round(time.time(), 1)
            samples.append(d)
            tf.write(json.dumps(d) + "\n")
            tf.flush()
            if d["tick"] - samples[0]["tick"] >= window_ticks:
                break
            time.sleep(5)
    proc.terminate()
    time.sleep(3)
    if proc.poll() is None:
        proc.kill()
    if not samples:
        results[i] = {"lane": lane_label, "error": "no samples"}
        return
    g = grade_s1(samples, window_ticks)
    results[i] = {"ts": time.time(), "lane": lane_label, "config": cfg_path,
                  "minutes": minutes, **g}
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
            for acct in a["accounts"]:
                accts.setdefault(acct, None)

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
    args = ap.parse_args()
    TL_DIR.mkdir(exist_ok=True)
    print("preflighting account pools…")
    preflight_accounts(args.lane)
    start_cluster(len(args.lane), args.save)
    results = {}
    threads = [threading.Thread(target=run_lane,
                                args=(i, cfg, args.label, args.minutes,
                                      results, bool(args.save)),
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
