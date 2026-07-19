"""Prove the save-crash patch: force a server save (what a joining player
triggers) and report whether the server survives. Run after FLE has injected
its tool library (i.e. while an agent run is active)."""

import subprocess
import time

from factorio_rcon import RCONClient

c = RCONClient("127.0.0.1", 27000, "factorio")
c.connect()
print("fns visible via proxy:", c.send_command("/sc rcon.print(type(storage.actions.get_lua_script_checksums))"))
print("issuing /server-save ...")
try:
    print("reply:", c.send_command("/server-save"))
except Exception as e:
    print("rcon dropped during save (bad sign):", e)

time.sleep(4)
log = subprocess.run(
    ["docker", "logs", "--since", "1m", "cluster-factorio_0-1"],
    capture_output=True, text=True,
    env={"PATH": "/Applications/Docker.app/Contents/Resources/bin:/usr/bin:/bin"},
).stdout + subprocess.run(
    ["docker", "logs", "--since", "1m", "cluster-factorio_0-1"],
    capture_output=True, text=True,
    env={"PATH": "/Applications/Docker.app/Contents/Resources/bin:/usr/bin:/bin"},
).stderr
saved = [l for l in log.splitlines() if "Saving" in l or "saved" in l or "Cannot serialise" in l or "non-recoverable" in l]
print("\n".join(saved[-6:]) or "(no save lines found in last minute of logs)")
try:
    print("post-save server alive:", c.send_command("/sc rcon.print(game.tick)"))
except Exception as e:
    print("SERVER DEAD after save:", e)
