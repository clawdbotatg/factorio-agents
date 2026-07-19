"""Live HUD for the FLE agent world.

Polls the Factorio server over RCON (~2s), tails the arena's per-agent JSONL
logs, AND reads each agent's real Claude session transcript from its account
config dir — so the HUD shows exactly what each brain was sent, what it
answered, and how long it thought. Serves a single page on :8790.

Run:  uv run python dashboard.py
Open: http://<this-mac-lan-ip>:8790
"""

import glob
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from factorio_rcon import RCONClient

PORT = 8790
RCON = ("127.0.0.1", 27000, "factorio")
HERE = Path(__file__).parent
LOG_DIR = HERE / "arena-logs"

try:
    from arena import AGENTS as ARENA_AGENTS  # module import is side-effect-safe
except Exception:
    ARENA_AGENTS = []

STATE_LUA = r"""
local out = {tick=game.tick, speed=game.speed, paused=game.tick_paused, players={}, agents={}, built={}}
for _,p in pairs(game.connected_players) do
  table.insert(out.players, {name=p.name, x=p.position.x, y=p.position.y})
end
for i,ch in pairs(storage.agent_characters or {}) do
  if ch and ch.valid then
    local a = {idx=i, x=ch.position.x, y=ch.position.y, health=ch.health or 0}
    local inv = ch.get_main_inventory and ch.get_main_inventory()
    if inv then
      local items = {}
      for _, item in pairs(inv.get_contents()) do
        items[item.name] = (items[item.name] or 0) + item.count
      end
      a.inventory = items
    end
    a.view = {}
    local nearby = ch.surface.find_entities_filtered{position=ch.position, radius=22}
    for _, e in pairs(nearby) do
      if #a.view >= 260 then break end
      if e.name ~= 'character' then
        table.insert(a.view, {n=e.name, t=e.type, x=e.position.x, y=e.position.y, d=e.direction or 0})
      end
    end
    table.insert(out.agents, a)
  end
end
for _, e in pairs(game.surfaces[1].find_entities_filtered{force='player'}) do
  if e.name ~= 'character' then out.built[e.name] = (out.built[e.name] or 0) + 1 end
end
rcon.print(helpers.table_to_json(out))
"""

snapshot = {"ok": False, "error": "starting up"}


def as_dict(v):
    return v if isinstance(v, dict) else {}


def parse_iso(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def tail_jsonl(path: Path, max_bytes=400_000):
    if not path.exists():
        return []
    with open(path, "rb") as f:
        f.seek(max(0, path.stat().st_size - max_bytes))
        raw = f.read().decode("utf-8", "replace")
    out = []
    for line in raw.splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def read_transcript(cfg: dict):
    """Newest Claude session transcript for this agent's workdir, searched
    across every account the brain can fail over to. Returns (msgs, account)
    where account is the one holding the newest session (= active pool)."""
    slug = cfg["name"].replace(" ", "_").lower()
    accounts = cfg.get("accounts") or [cfg.get("config_dir", "~/.claude")]
    files = []
    for acct in accounts:
        proj_root = Path(os.path.expanduser(acct)) / "projects"
        for dpath in glob.glob(str(proj_root / f"*{slug.replace('_', '?')}?workdir*")):
            for f in glob.glob(dpath + "/*.jsonl"):
                files.append((Path(f), Path(os.path.expanduser(acct)).name))
    if not files:
        return [], "?"
    newest, account = max(files, key=lambda fa: fa[0].stat().st_mtime)
    msgs = []
    for rec in tail_jsonl(newest):
        if rec.get("type") not in ("user", "assistant"):
            continue
        m = rec.get("message") or {}
        content = m.get("content")
        if isinstance(content, list):
            text = "\n".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ).strip()
            if not text and any(
                isinstance(b, dict) and b.get("type") == "thinking" for b in content
            ):
                text = "(thinking…)"
        else:
            text = str(content or "")
        if not text:
            continue
        msgs.append({"role": rec["type"], "text": text[:1500],
                     "ts": parse_iso(rec.get("timestamp", "") or "")})
    return msgs, account


def agent_snapshot():
    agents, chat = [], []
    now = time.time()
    for cfg in ARENA_AGENTS:
        name = cfg["name"]
        slug = name.replace(" ", "_").lower()
        events = tail_jsonl(LOG_DIR / f"{slug}.jsonl")
        msgs, active_account = read_transcript(cfg)

        # think times: assistant reply ts minus preceding user prompt ts
        thinks = []
        for i, m in enumerate(msgs):
            if m["role"] == "assistant" and m["ts"] and i > 0 and msgs[i - 1]["ts"] \
                    and msgs[i - 1]["role"] == "user":
                thinks.append(m["ts"] - msgs[i - 1]["ts"])

        if msgs and msgs[-1]["role"] == "user":
            status, since = "THINKING", msgs[-1]["ts"]
        elif msgs:
            status, since = "acting / waiting", msgs[-1]["ts"]
        else:
            status, since = "starting", None

        results = [e for e in events if e.get("kind") == "result"]
        metrics = [e for e in events if e.get("kind") == "metrics"]
        last_metrics = {}
        if metrics:
            try:
                last_metrics = json.loads(metrics[-1]["text"])
            except Exception:
                pass

        # team chat: send_message("...") in executed code
        for e in events:
            if e.get("kind") == "code":
                for m_ in re.findall(r"send_message\(\s*[\"'](.{3,220}?)[\"']\s*[,)]",
                                     e.get("text", "")):
                    chat.append({"agent": name, "ts": e.get("ts"), "text": m_})

        agents.append({
            "name": name,
            "model": cfg.get("model", "?"),
            "account": active_account,
            "brain": cfg.get("brain", "api"),
            "status": status,
            "status_s": round(now - since) if since else None,
            "last_think_s": round(thinks[-1]) if thinks else None,
            "avg_think_s": round(sum(thinks) / len(thinks)) if thinks else None,
            "exchanges": len([m for m in msgs if m["role"] == "assistant"]),
            "steps": len(results),
            "last_result": (results[-1]["text"][:800] if results else ""),
            "feed": msgs[-6:],
        })
    chat.sort(key=lambda c: c.get("ts") or 0)
    return agents, chat[-14:]


def poll_loop():
    global snapshot
    client = None
    while True:
        try:
            if client is None:
                client = RCONClient(*RCON)
                client.connect()
            raw = client.send_command("/sc " + STATE_LUA.replace("\n", " "))
            game = json.loads(raw)
            game["agents"] = game.get("agents") or []
            game["players"] = game.get("players") or []
            game["built"] = as_dict(game.get("built"))
            for a in game["agents"]:
                a["inventory"] = as_dict(a.get("inventory"))
                a["view"] = a.get("view") or []
            agents, chat = agent_snapshot()
            snapshot = {"ok": True, "ts": time.time(), "game": game,
                        "agents": agents, "chat": chat}
        except Exception as e:
            snapshot = {"ok": False, "ts": time.time(), "error": str(e)[:200]}
            client = None
        time.sleep(2)


PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FLE Agent HUD</title>
<style>
:root {
  --surface: #131318; --panel: #1c1c24; --edge: #2a2a35;
  --ink: #e9e9ee; --ink2: #a7a7b3; --ink3: #6d6d7a;
  --accent: #7fb4e6; --accent2: #c99ee6; --good: #79c398; --warn: #e0b568;
  font-size: 15px;
}
* { box-sizing: border-box; margin: 0; }
body { background: var(--surface); color: var(--ink);
  font: 400 1rem/1.45 -apple-system, "Segoe UI", sans-serif; padding: 16px; }
h1 { font-size: 1.05rem; font-weight: 600; letter-spacing: .04em; }
h1 .live { color: var(--good); font-size: .8rem; margin-left: .6em; }
h1 .dead { color: #de8686; font-size: .8rem; margin-left: .6em; }
.grid { display: grid; gap: 12px; margin-top: 12px;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
.panel { background: var(--panel); border: 1px solid var(--edge);
  border-radius: 8px; padding: 12px 14px; }
.panel h2 { font-size: .72rem; font-weight: 600; color: var(--ink3);
  text-transform: uppercase; letter-spacing: .1em; margin-bottom: 8px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px,1fr)); gap: 10px; }
.tile .v { font-size: 1.35rem; font-weight: 650; }
.tile .l { font-size: .68rem; color: var(--ink2); }
.kv { display: grid; grid-template-columns: 1fr auto; gap: 2px 12px; font-size: .85rem; }
.kv .k { color: var(--ink2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kv .n { text-align: right; font-variant-numeric: tabular-nums; }
.empty { color: var(--ink3); font-size: .85rem; }
.feed { max-height: 340px; overflow-y: auto; display: flex;
  flex-direction: column; gap: 6px; }
.msg { border-left: 3px solid var(--edge); padding: 4px 8px; font-size: .76rem;
  white-space: pre-wrap; color: var(--ink2);
  font-family: "SF Mono", ui-monospace, monospace; }
.msg.user { border-color: var(--warn); }
.msg.assistant { border-color: var(--accent); color: var(--ink); }
.msg .who { font-size: .65rem; text-transform: uppercase; letter-spacing: .08em;
  color: var(--ink3); }
.pill { display: inline-block; font-size: .68rem; padding: 2px 8px;
  border-radius: 10px; background: var(--edge); color: var(--ink2);
  margin-left: .6em; vertical-align: middle; }
.pill.think { background: #3a3050; color: var(--accent2); }
.chatline { font-size: .82rem; margin-bottom: 4px; }
.chatline .who { color: var(--accent); font-weight: 600; }
#map { width: 100%; aspect-ratio: 1; background: #101014; border-radius: 6px; }
.legend { font-size: .72rem; color: var(--ink2); margin-top: 6px; }
.legend span { margin-right: 1em; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: .35em; }
</style>
<h1>FLE AGENT HUD <span id="status" class="dead">connecting…</span></h1>
<div class="grid" id="agentgrid"></div>
<div class="grid">
  <div class="panel"><h2>Team chat (send_message)</h2><div id="chat"><span class="empty">quiet so far</span></div></div>
  <div class="panel"><h2>World</h2>
    <div class="tiles" id="world"></div>
    <div style="margin-top:8px"><svg id="map" viewBox="-120 -120 240 240"></svg></div>
    <div class="legend">
      <span><span class="dot" style="background:var(--accent)"></span>agents</span>
      <span><span class="dot" style="background:var(--good)"></span>you</span>
    </div>
  </div>
  <div class="panel"><h2>Built so far</h2><div class="kv" id="built"></div></div>
</div>
<script>
const $ = id => document.getElementById(id);
const esc = s => (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;");
function kv(el, obj, max=16) {
  const e = Object.entries(obj || {}).sort((a,b) => b[1]-a[1]);
  el.innerHTML = e.length ? e.slice(0,max).map(([k,v]) =>
    `<span class="k">${esc(k)}</span><span class="n">${v}</span>`).join("")
    : '<span class="empty">nothing yet</span>';
}
function tile(l, v) { return `<div class="tile"><div class="v">${v}</div><div class="l">${l}</div></div>`; }
function agentPanel(a, inv) {
  const think = a.status === "THINKING"
    ? `<span class="pill think">THINKING ${a.status_s ?? "?"}s…</span>`
    : `<span class="pill">${esc(a.status)} ${a.status_s != null ? a.status_s + "s ago" : ""}</span>`;
  const feed = (a.feed || []).map(m =>
    `<div class="msg ${m.role}"><div class="who">${m.role === "user" ? "→ sent to agent" : "← agent replied"}</div>${esc(m.text)}</div>`
  ).join("") || '<span class="empty">no transcript yet</span>';
  return `<div class="panel">
    <h2>${esc(a.name)} <span style="text-transform:none">· ${esc(a.model)} @ ${esc(a.account)} (${esc(a.brain)})</span>${think}</h2>
    <div class="tiles">
      ${tile("last think", a.last_think_s != null ? a.last_think_s + "s" : "–")}
      ${tile("avg think", a.avg_think_s != null ? a.avg_think_s + "s" : "–")}
      ${tile("replies", a.exchanges)}
      ${tile("programs run", a.steps)}
    </div>
    <h2 style="margin-top:10px">live view (40-tile schematic)</h2>
    <svg class="camview" viewBox="0 0 1 1" style="width:100%;aspect-ratio:1;background:#0d1a0d;border-radius:6px"></svg>
    <h2 style="margin-top:10px">conversation (live session transcript)</h2>
    <div class="feed">${feed}</div>
    ${a.last_result ? `<h2 style="margin-top:10px">last program output</h2><div class="msg">${esc(a.last_result)}</div>` : ""}
    ${inv ? `<h2 style="margin-top:10px">inventory</h2><div class="kv inv"></div>` : ""}
  </div>`;
}
async function tick() {
  try {
    const d = await (await fetch("data.json")).json();
    if (!d.ok) throw new Error(d.error || "no data");
    $("status").textContent = "LIVE"; $("status").className = "live";
    const g = d.game;
    // agent brain panels
    $("agentgrid").innerHTML = (d.agents || []).map((a, i) =>
      agentPanel(a, g.agents && g.agents[i])).join("");
    document.querySelectorAll("#agentgrid .inv").forEach((el, i) => {
      kv(el, (g.agents[i] || {}).inventory, 8);
    });
    const COLORS = {
      resource: "#2e6d6d", tree: "#1e4620", "simple-entity": "#3a3a30",
      "mining-drill": "#e08a3c", furnace: "#c05f4e", "assembling-machine": "#5f8fd6",
      "transport-belt": "#d9c04f", "underground-belt": "#b3a04a", splitter: "#d9c04f",
      inserter: "#7fd6d0", "electric-pole": "#cfcfd6", pipe: "#7a8fa6",
      "pipe-to-ground": "#7a8fa6", boiler: "#a67ac2", generator: "#a67ac2",
      "offshore-pump": "#5fb0d6", lab: "#d67ab8", container: "#b08a5f",
      "logistic-container": "#b08a5f", wall: "#999", radar: "#8aa",
    };
    document.querySelectorAll("#agentgrid .camview").forEach((svg, i) => {
      const ag = g.agents[i];
      if (!ag) return;
      const R = 22, S = 10;              // radius tiles, px per tile
      svg.setAttribute("viewBox", `0 0 ${2*R*S} ${2*R*S}`);
      let out = "";
      (ag.view || []).forEach(e => {
        const px = (e.x - ag.x + R) * S, py = (e.y - ag.y + R) * S;
        const c = COLORS[e.t] || COLORS[e.n] || "#666";
        if (e.t === "resource") {
          out += `<circle cx="${px}" cy="${py}" r="${S*0.35}" fill="${c}" opacity=".8"/>`;
        } else if (e.t === "tree") {
          out += `<circle cx="${px}" cy="${py}" r="${S*0.4}" fill="${c}"/>`;
        } else {
          const big = /assembling|furnace|boiler|generator|lab|drill|radar/.test(e.t) ? 1.8 : 0.9;
          const half = S * big / 2;
          out += `<rect x="${px-half}" y="${py-half}" width="${2*half}" height="${2*half}" fill="${c}" rx="1.5"><title>${esc(e.n)}</title></rect>`;
        }
      });
      out += `<circle cx="${R*S}" cy="${R*S}" r="${S*0.5}" fill="#fff" stroke="var(--accent)" stroke-width="2"/>`;
      svg.innerHTML = out;
    });
    // chat
    $("chat").innerHTML = (d.chat || []).map(c =>
      `<div class="chatline"><span class="who">${esc(c.agent)}:</span> ${esc(c.text)}</div>`
    ).join("") || '<span class="empty">quiet so far</span>';
    // world
    $("world").innerHTML =
      tile("tick", g.tick.toLocaleString()) + tile("speed", g.speed + "×") +
      tile("paused", g.paused ? "YES" : "no") +
      tile("humans", (g.players||[]).map(p=>p.name).join(", ") || "none");
    kv($("built"), g.built, 18);
    // map centered on centroid of agents
    const pts = (g.agents||[]).concat(g.players||[]);
    const cx = pts.length ? pts.reduce((s,p)=>s+p.x,0)/pts.length : 0;
    const cy = pts.length ? pts.reduce((s,p)=>s+p.y,0)/pts.length : 0;
    let dots = `<line x1="-120" y1="${-cy}" x2="120" y2="${-cy}" stroke="#22222c"/>` +
               `<line x1="${-cx}" y1="-120" x2="${-cx}" y2="120" stroke="#22222c"/>`;
    (g.players||[]).forEach(p => {
      dots += `<circle cx="${p.x-cx}" cy="${p.y-cy}" r="3.5" fill="var(--good)"><title>${esc(p.name)}</title></circle>`;
    });
    (g.agents||[]).forEach((ag, i) => {
      const nm = (d.agents[i]||{}).name || ("agent " + ag.idx);
      dots += `<circle cx="${ag.x-cx}" cy="${ag.y-cy}" r="4" fill="var(--accent)"><title>${esc(nm)}</title></circle>` +
              `<text x="${ag.x-cx+6}" y="${ag.y-cy+3}" fill="var(--ink3)" font-size="7">${esc(nm.split(" ")[0])}</text>`;
    });
    $("map").innerHTML = dots;
  } catch (e) {
    $("status").textContent = "NO DATA — " + e.message;
    $("status").className = "dead";
  }
  setTimeout(tick, 2000);
}
tick();
</script>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/data.json"):
            body = json.dumps(snapshot).encode()
            ctype = "application/json"
        elif self.path.startswith("/render/"):
            f = LOG_DIR / "render" / Path(self.path.split("?")[0]).name
            if f.suffix == ".png" and f.exists():
                body = f.read_bytes()
                ctype = "image/png"
            else:
                self.send_response(404); self.end_headers(); return
        else:
            body = PAGE.encode()
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=poll_loop, daemon=True).start()
    print(f"HUD on http://0.0.0.0:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
