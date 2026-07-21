"""Deterministic no-brain probe: run the S1 skill sequence at pinned speed 1
and time every skill. This is the ground-truth wall budget for a 5-minute
legal-mode Stage-1 plan (no LLM anywhere).

Usage: uv run python probe_skills.py [port]
"""

import asyncio
import os
import sys
import threading
import time

os.environ.setdefault("FLE_SPECTATOR_MODE", "1")

from factorio_rcon import RCONClient  # noqa: E402
from fle.env.a2a_instance import A2AFactorioInstance  # noqa: E402
from skills import PRELUDE  # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 27000
STOP = False


def pin_speed():
    c = RCONClient("127.0.0.1", PORT, "factorio")
    c.connect()
    while not STOP:
        try:
            c.send_command("/sc if game.speed ~= 1 then game.speed = 1 end")
        except Exception:
            pass
        time.sleep(2)


def main():
    global STOP
    inst = asyncio.run(A2AFactorioInstance.create(
        address="127.0.0.1", tcp_port=PORT, num_agents=1, fast=False,
        peaceful=True, clear_entities=True, reset_paused=False))
    threading.Thread(target=pin_speed, daemon=True).start()
    t_all = time.time()
    _, _, out = inst.eval(PRELUDE, agent_idx=0, timeout=60)
    print("prelude:", str(out)[:120])
    seq = [
        ("sk_gather(stone=22, coal=25, iron=30)", 240),
        ("sk_bootstrap_place()", 150),
        ("sk_bootstrap_feed()", 90),
        ("sk_keep_fed()", 150),
        ("sk_gather(iron=40, coal=20, stone=15)", 240),
        ("sk_keep_fed()", 150),
        ("sk_mine_line(resource='iron', n=2)", 150),
        ("sk_keep_fed()", 150),
        ("sk_power()", 240),
        ("sk_keep_fed()", 150),
        ("sk_status()", 60),
    ]
    for code, to in seq:
        t0 = time.time()
        try:
            _, _, out = inst.eval(code, agent_idx=0, timeout=to)
        except Exception as e:
            out = f"EVAL ERROR: {e}"
        print(f"\n=== {time.time()-t0:6.1f}s  {code}")
        print(str(out)[:700])
    print(f"\nTOTAL {time.time()-t_all:.0f}s wall")
    STOP = True


if __name__ == "__main__":
    main()
