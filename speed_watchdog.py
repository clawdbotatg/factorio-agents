"""Match-session watchdog: pin game.speed to 1 whenever a human is
connected (1s cadence — FLE init/sleeps can leave the game fast, and the
old 5s poll let a visible fast-forward slip through), keep the human admin,
and grant each newly-joined human the vanilla freeplay starter kit (parity:
FLE agents get it via the `inventory=` kwarg; the scenario gives joiners
nothing). Runs for 3h."""

import time
from factorio_rcon import RCONClient

KIT_LUA = (
    "/sc storage.fa_kit_granted = storage.fa_kit_granted or {} "
    "local granted = {} "
    "for _, p in pairs(game.connected_players) do "
    "if p.character and not storage.fa_kit_granted[p.name] then "
    "p.insert{name='burner-mining-drill', count=1} "
    "p.insert{name='stone-furnace', count=1} "
    "p.insert{name='iron-plate', count=8} "
    "p.insert{name='wood', count=1} "
    "storage.fa_kit_granted[p.name] = true "
    "table.insert(granted, p.name) end end "
    "rcon.print(#granted > 0 and table.concat(granted, ',') or 'none')"
)

PIN_LUA = (
    "/sc if #game.connected_players > 0 then local acted = false "
    "if game.speed ~= 1 then game.speed = 1 acted = true end "
    "if game.tick_paused then game.tick_paused = false acted = true end "
    "for _, p in pairs(game.connected_players) do "
    "if p.character == nil then p.create_character() acted = true end end "
    "rcon.print(acted and 'pinned' or 'ok') else rcon.print('ok') end"
)


def main():
    c = RCONClient("127.0.0.1", 27000, "factorio")
    c.connect()
    end = time.time() + 3 * 3600
    pins = 0
    i = 0
    while time.time() < end:
        try:
            i += 1
            if i % 30 == 1:
                try:
                    c.send_command("/promote austintgriffith")
                except Exception:
                    pass
            got = c.send_command(KIT_LUA)
            if got and got != "none":
                print(f"starter kit granted to: {got}", flush=True)
            if c.send_command(PIN_LUA) == "pinned":
                pins += 1
                print(f"speed re-pinned to 1 (total {pins})", flush=True)
        except Exception:
            try:
                c = RCONClient("127.0.0.1", 27000, "factorio")
                c.connect()
            except Exception:
                pass
        time.sleep(1)


if __name__ == "__main__":
    main()
