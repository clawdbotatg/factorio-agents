"""Pin game.speed to 1 while a human is spectating. FLE sets speed=10 during
setup/sleeps, which the box64-emulated server can't sustain for a lockstep
multiplayer client — the client times out and drops. Runs for 2h."""

import time
from factorio_rcon import RCONClient

c = RCONClient("127.0.0.1", 27000, "factorio")
c.connect()
end = time.time() + 7200
pins = 0
loop_i = 0
while time.time() < end:
    try:
        loop_i += 1
        if loop_i % 12 == 1:  # ~once a minute: keep the human admin across world resets
            try:
                c.send_command("/promote austintgriffith")
            except Exception:
                pass
        sp = c.send_command("/sc if #game.connected_players > 0 then local acted = false if game.speed > 1 then game.speed = 1 acted = true end if game.tick_paused then game.tick_paused = false acted = true end for _, p in pairs(game.connected_players) do if p.character == nil then p.create_character() acted = true end end rcon.print(acted and 'pinned' or 'ok') else rcon.print('ok') end")
        if sp == "pinned":
            pins += 1
            print(f"speed re-pinned to 1 (total {pins})", flush=True)
    except Exception:
        try:
            c = RCONClient("127.0.0.1", 27000, "factorio")
            c.connect()
        except Exception:
            pass
    time.sleep(5)
