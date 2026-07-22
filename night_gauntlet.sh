#!/bin/sh
# Ungated night runs: repeated full 20-min oven-line runs on the pinned lab
# seed. No kills — every run completes and logs its final score. Morning
# deliverable: a real distribution instead of gate-noise.
cd "$(dirname "$0")"
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PYTHONUNBUFFERED=1
i=0
while [ $i -lt 14 ]; do
  i=$((i+1))
  pkill -f "arena.py" 2>/dev/null; sleep 2
  uv run fle cluster stop >/dev/null 2>&1
  FLE_SEED=1804890437 FLE_SPACE_AGE=1 uv run fle cluster start -n 1 -s open_world >/dev/null 2>&1
  uv run python - <<'PYEOF'
import time
from factorio_rcon import RCONClient
for _ in range(90):
    try:
        c = RCONClient("127.0.0.1", 27000, "factorio"); c.connect()
        c.send_command("/sc rcon.print(1)"); break
    except Exception:
        time.sleep(4)
PYEOF
  ARENA_CONFIG=configs/vs-human.json ARENA_BOT_FORCE=1 ARENA_NO_RENDER=1 \
    ARENA_RCON_PORT=27000 FLE_SPECTATOR_MODE=1 RUN_LABEL=night-$i \
    nohup uv run python arena.py > night-run-$i.log 2>&1 &
  uv run python - <<'PYEOF'
import time, json
from factorio_rcon import RCONClient
c = RCONClient("127.0.0.1", 27000, "factorio"); c.connect()
PIN = "/sc if game.speed ~= 1 then game.speed = 1 end rcon.print('')"
Q = ('/sc local n=0 for _,e in pairs(game.surfaces[1].find_entities_filtered{force="bot"}) '
     'do if e.name~="character" then n=n+1 end end '
     'local p=game.forces["bot"].get_item_production_statistics(game.surfaces[1]).get_input_count("iron-plate") '
     'rcon.print(n .. "|" .. p)')
start = None
while True:
    try:
        c.send_command(PIN)
        n, p = map(int, c.send_command(Q).split("|"))
        if start is None and n > 0:
            start = time.time()
        if start and time.time() - start >= 20 * 60:
            with open("gauntlet-night.jsonl", "a") as f:
                f.write(json.dumps({"ts": time.time(), "built": n,
                                    "plates": p, "pts": n * 10 + p}) + "\n")
            print(f"NIGHT RUN DONE: {n*10+p} pts ({n} built, {p} plates)")
            break
        if start is None and time.time() % 1 < 0.1:
            pass
    except Exception:
        try:
            c = RCONClient("127.0.0.1", 27000, "factorio"); c.connect()
        except Exception:
            pass
    time.sleep(10)
PYEOF
  pkill -f "arena.py" 2>/dev/null
done
echo "NIGHT GAUNTLET COMPLETE"
