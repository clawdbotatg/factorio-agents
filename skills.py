"""Skills mode: LLM writes PRIORITIES, a scripted autopilot does the work.

The agent namespace gets a PRELUDE of reliable skill functions (mined from the
best programs in past match logs). The LLM never writes game code — it returns
a JSON priority queue of skill calls. The controller executes skills
back-to-back, running a keep_fed housekeeping sweep whenever the queue is
empty, and re-plans in a BACKGROUND thread so the character never stops
working while the model thinks.

Enable per-agent with "mode": "skills" in an arena config.
Self-test (compiles all generated code): python3 skills.py --selftest
"""

import json
import re
import threading
import time

# ------------------------------------------------------------- prelude ------
# Executed once in the agent's persistent FLE namespace. Every sk_* function
# is defensive: sweeps positions, catches everything, prints a ledger line.
PRELUDE = r'''
COAL_COLLECTORS = []  # (x, y) of furnaces that receive coal from coal drills

def _res(name):
    m = {"iron": "IronOre", "copper": "CopperOre", "coal": "Coal",
         "stone": "Stone", "water": "Water", "wood": "Wood"}
    return getattr(Resource, m.get(name, name))

def inv_count(proto):
    try:
        inv = inspect_inventory()
    except Exception:
        return 0
    for probe in (lambda: inv[proto], lambda: inv.get(proto, 0)):
        try:
            return probe() or 0
        except Exception:
            continue
    return 0

def try_place(proto, pos, direction=None, sweep=14):
    # walk to the area ONCE, then try nearby spots from where we stand —
    # every candidate is within build reach, so no per-attempt walking
    # (matters in legal-player mode where movement takes real time)
    offsets = [(0,0),(1,0),(-1,0),(0,1),(0,-1),(2,0),(-2,0),(0,2),(0,-2),
               (1,1),(-1,1),(1,-1),(-1,-1),(3,0),(-3,0),(0,3),(0,-3)][:sweep]
    try:
        move_to(pos)
    except Exception:
        pass
    for dx, dy in offsets:
        p = Position(x=pos.x + dx, y=pos.y + dy)
        try:
            if direction is not None:
                return place_entity(proto, position=p, direction=direction)
            return place_entity(proto, position=p)
        except Exception:
            continue
    return None

def sk_gather(stone=0, coal=0, iron=0, copper=0):
    print(f"SKILL gather stone={stone} coal={coal} iron={iron} copper={copper}")
    for name, amt in [("stone", stone), ("coal", coal),
                      ("iron", iron), ("copper", copper)]:
        if not amt:
            continue
        try:
            p = nearest(_res(name))
            move_to(p)
            harvest_resource(p, amt)
            print(f"harvested {amt} {name}")
        except Exception as e:
            print(f"gather {name} fail: {str(e)[:80]}")
    print(inspect_inventory())

def sk_smelt_bootstrap():
    print("SKILL smelt_bootstrap")
    try:
        craft_item(Prototype.StoneFurnace, 3)
        print("crafted 3 furnaces")
    except Exception as e:
        print("furnace craft fail:", str(e)[:90])
    ip = nearest(_res("iron"))
    placed = []
    for i in range(2):
        f = try_place(Prototype.StoneFurnace,
                      Position(x=ip.x + i * 3, y=ip.y - 7))
        if f:
            placed.append(f)
    print(f"placed {len(placed)} bootstrap furnaces")
    for f in placed:
        try:
            move_to(f.position)
            insert_item(Prototype.Coal, f, quantity=10)
            insert_item(Prototype.IronOre, f, quantity=24)
        except Exception as e:
            print("feed fail:", str(e)[:70])
    sleep(25)
    for f in placed:
        try:
            move_to(f.position)
            got = extract_item(Prototype.IronPlate, f, quantity=48)
            print(f"extracted plates: {got}")
        except Exception as e:
            print("extract fail:", str(e)[:70])
    print(inspect_inventory())

def sk_mine_line(resource="iron", n=3):
    print(f"SKILL mine_line {resource} n={n}")
    need = max(0, n - inv_count(Prototype.BurnerMiningDrill))
    if need:
        try:
            craft_item(Prototype.BurnerMiningDrill, need)
            print(f"crafted {need} drills")
        except Exception as e:
            print("drill craft fail:", str(e)[:90])
    try:
        craft_item(Prototype.StoneFurnace, n)
    except Exception as e:
        print("furnace craft fail:", str(e)[:90])
    patch = nearest(_res(resource))
    placed = 0
    for i in range(n):
        base = Position(x=patch.x + (i % 4) * 4 - 6,
                        y=patch.y + (i // 4) * 7)
        d = try_place(Prototype.BurnerMiningDrill, base, Direction.DOWN)
        if d is None:
            print(f"no spot for drill {i}")
            continue
        placed += 1
        try:
            insert_item(Prototype.Coal, d, quantity=8)
        except Exception:
            pass
        f = None
        try:
            f = place_entity(Prototype.StoneFurnace, position=d.drop_position)
        except Exception:
            pass
        if f:
            if resource == "coal":
                COAL_COLLECTORS.append((round(f.position.x), round(f.position.y)))
            else:
                try:
                    insert_item(Prototype.Coal, f, quantity=8)
                except Exception:
                    pass
    print(f"placed {placed}/{n} drills with drop furnaces")
    print(inspect_inventory())

def sk_power():
    print("SKILL power")
    for proto, qty in [(Prototype.OffshorePump, 1), (Prototype.Boiler, 1),
                       (Prototype.SteamEngine, 2), (Prototype.Pipe, 10),
                       (Prototype.SmallElectricPole, 8)]:
        try:
            craft_item(proto, qty)
        except Exception as e:
            print(f"craft fail {proto}: {str(e)[:70]}")
    water = nearest(_res("water"))
    pump = None
    for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1),(2,0),(-2,0),(0,2),(0,-2)]:
        for d in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT):
            try:
                p = Position(x=water.x + dx, y=water.y + dy)
                try:
                    move_to(Position(x=p.x, y=p.y - 3))
                except Exception:
                    pass
                pump = place_entity(Prototype.OffshorePump, position=p, direction=d)
                break
            except Exception:
                continue
        if pump:
            break
    if not pump:
        print("pump placement failed everywhere")
        return
    print(f"pump at {pump.position}")
    try:
        boiler = place_entity_next_to(Prototype.Boiler, pump.position,
                                      Direction.UP, spacing=2)
        insert_item(Prototype.Coal, boiler, quantity=20)
        connect_entities(pump, boiler, Prototype.Pipe)
        prev = boiler
        engines = 0
        for _ in range(2):
            eng = None
            for d in (Direction.UP, Direction.RIGHT, Direction.LEFT, Direction.DOWN):
                try:
                    eng = place_entity_next_to(Prototype.SteamEngine,
                                               prev.position, d, spacing=2)
                    connect_entities(prev, eng, Prototype.Pipe)
                    break
                except Exception:
                    continue
            if eng is None:
                break
            engines += 1
            prev = eng
        print(f"power online: boiler + {engines} engines")
    except Exception as e:
        print("power build error:", str(e)[:120])

def sk_expand_smelting(n=4):
    print(f"SKILL expand_smelting n={n}")
    try:
        craft_item(Prototype.StoneFurnace, n)
    except Exception as e:
        print("craft fail:", str(e)[:80])
    ip = nearest(_res("iron"))
    placed = 0
    for i in range(n):
        f = try_place(Prototype.StoneFurnace,
                      Position(x=ip.x - 10 + (i % 6) * 3, y=ip.y - 10))
        if f:
            placed += 1
            try:
                insert_item(Prototype.Coal, f, quantity=8)
            except Exception:
                pass
    print(f"placed {placed} smelting furnaces (autopilot feeds them ore)")

def sk_craft(item="IronGearWheel", n=1):
    print(f"SKILL craft {item} x{n}")
    proto = getattr(Prototype, item, None)
    if proto is None:
        print(f"unknown prototype {item}")
        return
    try:
        made = craft_item(proto, n)
        print(f"crafted {made}")
    except Exception as e:
        print("craft fail:", str(e)[:100])
    print(inspect_inventory())

def sk_keep_fed(radius=150):
    acts = []
    if inv_count(Prototype.Coal) < 15:
        try:
            p = nearest(_res("coal"))
            move_to(p)
            harvest_resource(p, 40)
            acts.append("mined 40 coal")
        except Exception as e:
            acts.append("coal restock fail " + str(e)[:40])
    try:
        ents = get_entities(radius=radius)
    except Exception:
        ents = []
    fueled = swept = 0
    collectors = set(COAL_COLLECTORS)
    for e in ents:
        try:
            nm = e.name
            if nm == "stone-furnace":
                move_to(e.position)
                if (round(e.position.x), round(e.position.y)) in collectors:
                    try:
                        got = extract_item(Prototype.Coal, e, quantity=50)
                        if got:
                            swept += 1
                    except Exception:
                        pass
                    continue
                if inv_count(Prototype.Coal) > 6:
                    try:
                        insert_item(Prototype.Coal, e, quantity=4)
                        fueled += 1
                    except Exception:
                        pass
                for proto in (Prototype.IronPlate, Prototype.CopperPlate):
                    try:
                        got = extract_item(proto, e, quantity=50)
                        if got:
                            swept += 1
                    except Exception:
                        pass
                if inv_count(Prototype.IronOre) > 40:
                    try:
                        insert_item(Prototype.IronOre, e, quantity=15)
                    except Exception:
                        pass
            elif nm in ("burner-mining-drill", "boiler", "burner-inserter"):
                if inv_count(Prototype.Coal) > 6:
                    move_to(e.position)
                    try:
                        insert_item(Prototype.Coal, e, quantity=4)
                        fueled += 1
                    except Exception:
                        pass
        except Exception:
            pass
    print(f"keep_fed: fueled={fueled} swept={swept} {' | '.join(acts)}")
    print(inspect_inventory())

def sk_status():
    inv = inspect_inventory()
    ents = {}
    try:
        for e in get_entities(radius=180):
            ents[e.name] = ents.get(e.name, 0) + 1
    except Exception:
        pass
    print("INV:", inv)
    print("BUILT:", ents)

print("PRELUDE LOADED — skills:", [k for k in dir() if k.startswith("sk_")])
'''

# ---------------------------------------------------------- controller ------
SKILLS = {  # name -> (timeout_s, allowed arg keys)
    # timeouts sized for legal-player mode (fast=False): walking between
    # patches and real craft times make every skill several times slower
    "gather":          (280, {"stone", "coal", "iron", "copper"}),
    "smelt_bootstrap": (280, set()),
    "mine_line":       (340, {"resource", "n"}),
    "power":           (340, set()),
    "expand_smelting": (280, {"n"}),
    "craft":           (220, {"item", "n"}),
    "keep_fed":        (280, {"radius"}),
}

DEFAULT_PLAN = [
    {"skill": "gather", "args": {"stone": 15, "coal": 25, "iron": 30}},
    {"skill": "smelt_bootstrap", "args": {}},
    {"skill": "mine_line", "args": {"resource": "iron", "n": 3}},
    {"skill": "gather", "args": {"stone": 20, "coal": 30}},
    {"skill": "mine_line", "args": {"resource": "coal", "n": 2}},
    {"skill": "power", "args": {}},
    {"skill": "mine_line", "args": {"resource": "iron", "n": 3}},
]

CATALOG = """You are the STRATEGY BRAIN for a Factorio agent. You never write
game code — a reliable scripted autopilot executes SKILLS; you choose and
order them. Between your decisions the autopilot constantly runs keep_fed
(refuels every burner, sweeps finished plates out of furnaces, feeds spare
ore in, restocks coal by hand-mining) — so build maintenance is FREE. Your
job is expansion strategy: what to build next, how much, in what order.

SKILL CATALOG (args -> effect, rough prerequisites):
- gather {stone,coal,iron,copper}: hand-mine raw resources. Fast. No prereqs.
- smelt_bootstrap {}: place 2 furnaces at the iron patch, smelt starter
  plates. Needs ~15 stone, ~10 coal, ~24 iron ore in inventory.
- mine_line {resource: iron|copper|coal|stone, n}: place n burner drills,
  each with a drop-feed furnace — a self-running mine+smelt line. Auto-crafts
  drills/furnaces first: needs ~9 iron plates + ~10 stone per drill.
  A coal mine_line's furnaces act as coal collectors the autopilot empties.
- power {}: offshore pump + boiler + 2 steam engines, piped. Needs ~35 iron
  plates, ~10 stone. Prereq for any electric machines later.
- expand_smelting {n}: n extra furnaces near the iron patch; the autopilot
  feeds them from your ore inventory.
- craft {item, n}: hand-craft any prototype by name (recursive — crafts
  intermediates), e.g. {"item": "BurnerMiningDrill", "n": 2}.
- keep_fed {}: one extra maintenance sweep (usually unnecessary — automatic).

SCORING: 10 pts per entity built + 1 pt per item produced. Self-running
drill+furnace pairs compound; get many running EARLY, then widen.

Reply with ONLY a JSON object, no prose, no code fences:
{"note": "<one-line strategy>",
 "priorities": [{"skill": "gather", "args": {"stone": 15, "coal": 25, "iron": 30}}, ...]}
Queue 3-6 priorities. Each reply REPLACES the remaining queue. You are
re-consulted with fresh status every ~90 seconds while the autopilot works."""


def _parse_plan(text: str):
    """Extract {"priorities": [...]} from an LLM reply; None if unusable."""
    m = text.find("{")
    if m < 0:
        return None, None
    try:
        data = json.loads(re.sub(r"```(?:json)?|```", "", text[m:text.rfind("}") + 1]))
    except Exception:
        return None, None
    if "priorities" not in data:
        return None, None
    plan = []
    for item in data.get("priorities") or []:
        name = item.get("skill")
        if name not in SKILLS:
            continue
        args = item.get("args") or {}
        allowed = SKILLS[name][1]
        plan.append({"skill": name,
                     "args": {k: v for k, v in args.items() if k in allowed}})
    # an explicit empty list is a legal strategy: "just run keep_fed"
    return plan, data.get("note")


def _invocation(item) -> str:
    kw = ", ".join(f"{k}={json.dumps(v)}" for k, v in item["args"].items())
    return f"sk_{item['skill']}({kw})"


def run_skills_agent(instance, idx: int, cfg: dict, shared_goal: str,
                     brain_cls, log, max_steps: int = 400):
    name = cfg["name"]
    system = (CATALOG + "\n\n" + cfg.get("persona", "")
              + "\n\nMATCH CONTEXT:\n" + shared_goal)
    brain = brain_cls(name, cfg["model"], cfg["accounts"], system)

    score, _, out = instance.eval(PRELUDE, agent_idx=idx, timeout=60)
    log(name, "prelude", str(out)[:400])
    inline_prelude = "PRELUDE LOADED" not in str(out) or "Error" in str(out)[:80]
    if inline_prelude:
        log(name, "prelude", "namespace persistence unclear — inlining prelude per skill")

    home = cfg.get("home")
    if home:
        try:
            instance.eval(
                f"move_to(Position(x={home[0]}, y={home[1]}))\n"
                f"print('at home sector {home}')", agent_idx=idx, timeout=60)
            log(name, "home", str(home))
        except Exception as e:
            log(name, "home", f"move failed: {e}")

    state = {"queue": list(DEFAULT_PLAN), "inflight": False, "last_plan": 0.0}
    lock = threading.Lock()
    history = []
    t0 = time.time()

    def build_status(last_result: str, score) -> str:
        try:
            _, _, st = instance.eval("sk_status()" if not inline_prelude
                                     else PRELUDE + "\nsk_status()",
                                     agent_idx=idx, timeout=30)
        except Exception as e:
            st = f"status error: {e}"
        with lock:
            qtxt = json.dumps(state["queue"])
        done = "; ".join(history[-8:])
        return (f"STATUS at minute {(time.time() - t0) / 60:.1f} "
                f"(production score {score}):\n{str(st)[:1200]}\n"
                f"Recently executed: {done or 'nothing yet'}\n"
                f"Last skill output:\n{str(last_result)[:700]}\n"
                f"Remaining queue (you may replace it): {qtxt}\n"
                "Reply ONLY with the JSON plan object.")

    def plan_async(status: str):
        def work():
            try:
                reply = brain.think(status)
                log(name, "thought", reply)
                plan, note = _parse_plan(reply)
                if plan is not None:
                    with lock:
                        state["queue"] = plan
                    log(name, "plan", json.dumps(
                        {"note": note, "priorities": plan}))
                else:
                    log(name, "plan-parse-fail", reply[:300])
            except Exception as e:
                log(name, "brain-error", str(e)[:200])
            finally:
                state["inflight"] = False
                state["last_plan"] = time.time()
        state["inflight"] = True
        threading.Thread(target=work, daemon=True,
                         name=f"{name}-planner").start()

    last_result = ""
    for step in range(1, max_steps + 1):
        with lock:
            item = state["queue"].pop(0) if state["queue"] else None
        if item is None:
            item = {"skill": "keep_fed",
                    "args": ({"radius": cfg["sweep_radius"]}
                             if cfg.get("sweep_radius") else {})}
        inv = _invocation(item)
        code = inv if not inline_prelude else PRELUDE + "\n" + inv
        timeout = SKILLS[item["skill"]][0]
        log(name, "code", inv)
        try:
            score, _, result = instance.eval(code, agent_idx=idx,
                                             timeout=timeout)
        except Exception as e:
            score, result = None, f"eval error: {e}"
        last_result = str(result)
        log(name, "result", last_result)
        ok = "Error" not in last_result[:200] and "error" not in last_result[:120]
        history.append(f"{inv} -> {'ok' if ok else 'FAIL'}")
        try:
            ec = int(instance.rcon_client.send_command(
                "/sc rcon.print(game.surfaces[1].count_entities_filtered{force='player'})"))
        except Exception:
            ec = None
        log(name, "score", json.dumps(
            {"step": step, "score": score, "entities": ec,
             "skill": item["skill"]}))
        if (not state["inflight"]
                and time.time() - state["last_plan"] > cfg.get("plan_every_s", 90)):
            plan_async(build_status(last_result, score))
        time.sleep(1)
    log(name, "done", f"completed {max_steps} skill steps")


# ------------------------------------------------------------- selftest -----
if __name__ == "__main__":
    compile(PRELUDE, "<prelude>", "exec")
    for nm in SKILLS:
        item = {"skill": nm,
                "args": {"resource": "iron", "n": 2, "stone": 5, "coal": 5,
                         "iron": 5, "copper": 0, "item": "Pipe"}}
        item["args"] = {k: v for k, v in item["args"].items()
                        if k in SKILLS[nm][1]}
        compile(_invocation(item), "<inv>", "eval")
    good, note = _parse_plan('here you go```json\n{"note":"x","priorities":'
                             '[{"skill":"gather","args":{"iron":10}},'
                             '{"skill":"bogus","args":{}}]}\n```')
    assert good == [{"skill": "gather", "args": {"iron": 10}}], good
    print("selftest OK — prelude and invocations compile, plan parser works")
