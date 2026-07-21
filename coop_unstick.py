"""Match-legal unstick for live sessions: if the bot's walking queue is
non-empty and its character hasn't moved for ~15s, clear ITS OWN walking
queue (a player deciding to stop walking — not a world modification). The
hung move_to's long-poll sees the empty queue and returns, the skill fails
cleanly, and the brain re-plans. Logs every intervention."""

import time
from factorio_rcon import RCONClient

POLL = (
    "/sc local wq = -1 "
    "local ok, v = pcall(function() return fle_actions.get_walking_queue_length(1) end) "
    "if ok then wq = tonumber(v) or -1 end "
    "local ch = storage.agent_characters and storage.agent_characters[1] "
    "local cx, cy = 0, 0 "
    "if ch and ch.valid then cx, cy = ch.position.x, ch.position.y end "
    "rcon.print(wq .. '|' .. cx .. '|' .. cy)"
)

CLEAR = (
    "/sc local ok = pcall(function() fle_actions.clear_walking_queue(1) end) "
    "rcon.print(ok and 'cleared' or 'clear failed')"
)


def main():
    c = RCONClient("127.0.0.1", 27000, "factorio")
    c.connect()
    last = None
    stuck_since = None
    clears = 0
    while True:
        try:
            wq, cx, cy = c.send_command(POLL).split("|")
            # round position: a character shoving a wall 'walks' in place
            # with sub-tile jitter — exact comparison never matches
            state = (wq, round(float(cx)), round(float(cy)))
            if int(float(wq)) > 0 and state == last:
                if stuck_since is None:
                    stuck_since = time.time()
                elif time.time() - stuck_since > 15:
                    print(f"stuck {time.time()-stuck_since:.0f}s at ({cx},{cy}) "
                          f"wq={wq} -> {c.send_command(CLEAR)}", flush=True)
                    clears += 1
                    stuck_since = None
            else:
                stuck_since = None
            last = state
        except Exception:
            try:
                c = RCONClient("127.0.0.1", 27000, "factorio")
                c.connect()
            except Exception:
                pass
        time.sleep(3)


if __name__ == "__main__":
    main()
