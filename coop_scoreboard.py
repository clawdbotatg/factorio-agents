"""Live match scoreboard: every 30s, census entities by placer (human via
last_user, bot = FLE-placed with no last_user) and print the score into the
GAME CHAT plus stdout. Only reports while a human is connected."""

import time
from factorio_rcon import RCONClient

LUA = (
    "/sc if #game.connected_players == 0 then rcon.print('nobody') else "
    "local function side(force_name) "
    "local f = game.forces[force_name] "
    "if not f then return 0, 0 end "
    "local n = 0 "
    "for _, e in pairs(game.surfaces[1].find_entities_filtered{force=force_name}) do "
    "if e.name ~= 'character' then n = n + 1 end end "
    "local plates = f.get_item_production_statistics(game.surfaces[1])"
    ".get_input_count('iron-plate') "
    "return n, plates end "
    "local hn, hp = side('player') "
    "local bn, bp = side('bot') "
    "local m = math.floor(game.tick / 3600) "
    "local s = math.floor(game.tick / 60) % 60 "
    "local hs = hn * 10 + hp "
    "local bs = bn * 10 + bp "
    "local lead = (hs > bs) and 'YOU LEAD' or ((bs > hs) and 'BOT LEADS' or 'TIED') "
    "local msg = string.format('[RACE %d:%02d] You: %d pts (%d built, %d plates)  vs  "
    "Bot: %d pts (%d built, %d plates)  — %s', m, s, hs, hn, hp, bs, bn, bp, lead) "
    "game.print(msg) rcon.print(msg) end"
)


def main():
    c = RCONClient("127.0.0.1", 27000, "factorio")
    c.connect()
    while True:
        try:
            out = c.send_command(LUA)
            if out and out != "nobody":
                print(out, flush=True)
        except Exception:
            try:
                c = RCONClient("127.0.0.1", 27000, "factorio")
                c.connect()
            except Exception:
                pass
        time.sleep(30)


if __name__ == "__main__":
    main()
