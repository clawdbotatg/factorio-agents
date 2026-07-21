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
# NOTE: keep the prelude functions-only — FLE's namespace persistence drops
# module imports and non-trivial top-level state between evals (probe: a
# top-level list assigned in one eval NameErrors in the next).

# Legal-mode ClientBusy armor (s1-batch2 finding): a timed-out walk keeps
# running server-side and later calls die with "client is already busy".
# _b(fn, ...) waits out the in-flight action instead of failing. This is an
# EXPLICIT wrapper, not a monkeypatch -- shadowing FLE's injected tool names
# at prelude scope breaks their name resolution (s1-batch3: NameError on
# every primitive).
def _b(fn, *a, **k):
    last = None
    for _ in range(8):
        try:
            return fn(*a, **k)
        except Exception as e:
            if "already busy" not in str(e):
                raise
            last = e
            sleep(4)
    raise last

def _hv(p, amt):
    # MATCH PHYSICS: FLE hand-harvest is ~50x vanilla — the one big cheat in
    # "legal" mode (WR-PACE §6). Charge vanilla hand-mining time (0.5
    # items/s -> 2 game-seconds per item) via tick-aware sleep, so the
    # charge is correct at any lab speed. Parity audit of craft/walk: TODO.
    r = _b(harvest_resource, p, amt)
    sleep(int(amt * 2))
    return r

def _escape():
    # Self-rescue (match-legal: mining YOUR OWN building): if every path out
    # fails, pick up one adjacent own entity to open a gap. First live match
    # ended with the bot entombed in its own mine line — a human had to dig
    # it out. The item returns to inventory; nothing is lost.
    try:
        for e in get_entities(radius=3):
            try:
                if e.name == "character":
                    continue
                got = _b(pickup_entity, e)
                print(f"ESCAPE: picked up own {e.name} to open a path")
                return True
            except Exception:
                continue
    except Exception:
        pass
    return False

def _near(pos):
    # walk NEXT TO a target tile, never onto it: pathing onto an occupied
    # tile hangs the legal-mode pathfinder and zombifies the client (the
    # bootstrap_feed 150s wedge — s1 probe finding)
    for attempt in (1, 2):
        for dx, dy in ((2.5, 0), (-2.5, 0), (0, 2.5), (0, -2.5), (3, 3), (-3, -3)):
            try:
                _b(move_to, Position(x=pos.x + dx, y=pos.y + dy))
                return True
            except Exception:
                continue
        if attempt == 1 and not _escape():
            break
    return False

def _fuel(e, qty):
    # coal first, WOOD as fallback — a map can fence off its coal (first
    # live match: coal under crash-site wreckage; boiler fueling failed one
    # step from power while wood stood everywhere)
    if inv_count(Prototype.Coal) > 6:
        return _touch(insert_item, Prototype.Coal, e, quantity=qty)
    if inv_count(Prototype.Wood) > 2:
        return _touch(insert_item, Prototype.Wood, e, quantity=min(qty * 2, 10))
    raise Exception("no fuel in inventory (coal or wood)")

def _touch(fn, *a, **k):
    # act on an entity: try from where we stand first (reach ~10 tiles);
    # only walk adjacent if the action itself refuses
    try:
        return _b(fn, *a, **k)
    except Exception:
        ent = a[1] if len(a) > 1 else None
        pos = getattr(ent, "position", None)
        if pos is None:
            raise
        _near(pos)
        return _b(fn, *a, **k)


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
    # Stand OFF the build spot, then place within reach (~10 tiles): placing
    # an entity over the character ENTOMBS it — its walking queue can never
    # drain and every later move_to long-polls forever (the s1 probe wedge:
    # char found embedded inside its own furnace). Never build where you
    # stand.
    offsets = [(0,0),(1,0),(-1,0),(0,1),(0,-1),(2,0),(-2,0),(0,2),(0,-2),
               (1,1),(-1,1),(1,-1),(-1,-1),(3,0),(-3,0),(0,3),(0,-3)][:sweep]
    try:
        _b(move_to, Position(x=pos.x, y=pos.y + 4))
    except Exception:
        pass
    for dx, dy in offsets:
        p = Position(x=pos.x + dx, y=pos.y + dy)
        try:
            if direction is not None:
                return _b(place_entity, proto, position=p, direction=direction)
            return _b(place_entity, proto, position=p)
        except Exception:
            continue
    return None

def sk_gather(stone=0, coal=0, iron=0, copper=0):
    print(f"SKILL gather stone={stone} coal={coal} iron={iron} copper={copper}")
    # iron/coal first — the stone patch is the far one on this seed and its
    # walk is the recurring pathfinder-wedge site; don't let it block the rest
    for name, amt in [("iron", iron), ("coal", coal),
                      ("stone", stone), ("copper", copper)]:
        if not amt:
            continue
        path_fails = 0
        for attempt in (1, 2, 3):  # nearest()/path service flake transiently
            try:
                p = nearest(_res(name))
                _b(move_to, p)
                _hv( p, amt)
                print(f"harvested {amt} {name}")
                break
            except Exception as e:
                msg = str(e)
                if "path" in msg.lower() or "Cannot move" in msg:
                    path_fails += 1
                    # two strikes: single path errors are usually transient
                    # (rematch: 5 false 'unreachable' reports on patches that
                    # worked minutes later); only consecutive ones are terrain
                    if path_fails >= 2:
                        print(f"PATH BLOCKED to {name} (2 consecutive) — "
                              "treat patch as unreachable; use wood for fuel")
                        break
                    sleep(3)
                    continue
                print(f"gather {name} fail (try {attempt}): {msg[:80]}")
                if attempt < 3:
                    sleep(3)
    print(inspect_inventory())

def sk_bootstrap_place():
    """Quantum 1: provision inputs, craft 3 furnaces, place 2 at the iron
    patch. NO feeding, NO waiting — bootstrap_feed and keep_fed do the rest.
    (The old monolithic smelt_bootstrap blew every stage timeout.)"""
    print("SKILL bootstrap_place")
    # 4 furnaces worth of stone: 2 placed + 1 reserved for the boiler craft
    # (sk_power) + 1 spare for a mine_line drop furnace
    for res, proto, need, grab in [("stone", Prototype.Stone, 20, 22),
                                   ("coal", Prototype.Coal, 10, 20),
                                   ("iron", Prototype.IronOre, 24, 30)]:
        if inv_count(proto) < need:
            try:
                p = nearest(_res(res))
                _b(move_to, p)
                _hv( p, grab)
                print(f"self-provisioned {grab} {res}")
            except Exception as e:
                print(f"{res} self-provision fail: {str(e)[:60]}")
    try:
        _b(craft_item, Prototype.StoneFurnace, 4)
        print("crafted 4 furnaces")
    except Exception as e:
        print("furnace craft fail:", str(e)[:90])
    ip = nearest(_res("iron"))
    placed = 0
    for i in range(2):
        f = try_place(Prototype.StoneFurnace,
                      Position(x=ip.x + i * 3, y=ip.y - 7))
        if f:
            placed += 1
    print(f"placed {placed} bootstrap furnaces "
          "(keeping spares: 1 for boiler, 1 for a drop furnace)")
    print(inspect_inventory())

def sk_bootstrap_feed():
    """Quantum 2: walk the nearby stone furnaces, load coal + iron ore from
    inventory. Plates get swept out later by keep_fed."""
    print("SKILL bootstrap_feed")
    try:
        ents = get_entities(radius=60)
    except Exception:
        ents = []
    fed = 0
    for e in ents:
        try:
            if e.name != "stone-furnace":
                continue
            _fuel(e, 10)
            _touch(insert_item, Prototype.IronOre, e, quantity=24)
            fed += 1
        except Exception as err:
            print("feed fail:", str(err)[:70])
    print(f"fed {fed} furnaces")
    print(inspect_inventory())

def sk_mine_line(resource="iron", n=3):
    print(f"SKILL mine_line {resource} n={n}")
    plates = inv_count(Prototype.IronPlate)
    craftable = inv_count(Prototype.BurnerMiningDrill) + plates // 9
    if craftable == 0:
        print(f"BLOCKED mine_line: 0 drills craftable (iron plates={plates}, "
              "~9 needed per drill). Run smelt_bootstrap / gather first.")
        return
    if n > craftable:
        print(f"capping n {n} -> {craftable} (plates limit)")
        n = craftable
    need = max(0, n - inv_count(Prototype.BurnerMiningDrill))
    if need:
        try:
            _b(craft_item, Prototype.BurnerMiningDrill, need)
            print(f"crafted {need} drills")
        except Exception as e:
            print("drill craft fail:", str(e)[:90])
    furn_craftable = inv_count(Prototype.Stone) // 5
    furn_want = max(0, n - inv_count(Prototype.StoneFurnace))
    if furn_want > furn_craftable:
        # self-provision the missing stone (rematch: the stone economy
        # starved every mine line while a human just went and got stone)
        try:
            p = nearest(_res("stone"))
            _b(move_to, p)
            _hv( p, (furn_want - furn_craftable) * 5 + 4)
            furn_craftable = inv_count(Prototype.Stone) // 5
            print(f"self-provisioned stone -> {furn_craftable} furnaces craftable")
        except Exception as e:
            print(f"low stone and stone trip failed ({str(e)[:50]}) — "
                  f"placing {furn_craftable} drop furnaces only")
    if min(furn_want, furn_craftable):
        try:
            _b(craft_item, Prototype.StoneFurnace, min(furn_want, furn_craftable))
        except Exception as e:
            print("furnace craft fail:", str(e)[:90])
    patch = nearest(_res(resource))
    placed = 0
    # ONE-PASS CARPET ROW: walk the lane 4 south of the row ONCE, placing
    # drills at reach (~10 tiles) as we pass — the technique a human uses to
    # drop 15 drills in a minute (match 2: human carpet vs bot zigzag, 3x).
    # Single open row, builder always south of everything: never enclose
    # the builder (match 1 entombment).
    lane_y = patch.y + 4
    for i in range(n):
        bx = patch.x + i * 4 - (n // 2) * 4
        if i % 2 == 0:  # step the lane every other drill, stay in reach
            try:
                _b(move_to, Position(x=bx, y=lane_y))
            except Exception:
                pass
        d = None
        for dy in (0, 1, -1):
            try:
                d = _b(place_entity, Prototype.BurnerMiningDrill,
                       position=Position(x=bx, y=patch.y + dy),
                       direction=Direction.DOWN)
                break
            except Exception:
                continue
        if d is None:
            print(f"no spot for drill {i}")
            continue
        placed += 1
        try:
            _touch(insert_item, Prototype.Coal, d, quantity=8)
        except Exception:
            pass
        f = None
        try:
            f = _b(place_entity, Prototype.StoneFurnace, position=d.drop_position)
        except Exception:
            pass
        if f:
            if resource == "coal":
                COAL_COLLECTORS.append((round(f.position.x), round(f.position.y)))
            else:
                try:
                    _touch(insert_item, Prototype.Coal, f, quantity=8)
                except Exception:
                    pass
    print(f"placed {placed}/{n} drills with drop furnaces")
    print(inspect_inventory())

def sk_power_craft():
    """Power quantum 1: craft pump + boiler + 2 engines + pipes near base.
    Cheap, no long walks. Follow with power_build."""
    print("SKILL power_craft")
    plates = inv_count(Prototype.IronPlate)
    have_parts = (inv_count(Prototype.OffshorePump)
                  and inv_count(Prototype.Boiler)
                  and inv_count(Prototype.SteamEngine) >= 2)
    if have_parts:
        print("power parts already crafted — run power_build")
        return
    if plates < 30:
        print(f"BLOCKED power_craft: need ~35 iron plates (have {plates}). "
              "Smelt more first (bootstrap/mine_line + keep_fed).")
        return
    # boiler consumes a stone furnace — self-provision the stone if short
    if (not inv_count(Prototype.Boiler)
            and not inv_count(Prototype.StoneFurnace)
            and inv_count(Prototype.Stone) < 5):
        try:
            p = nearest(_res("stone"))
            _b(move_to, p)
            _hv( p, 8)
            print("self-provisioned 8 stone for the boiler")
        except Exception as e:
            print("BLOCKED power_craft: no stone for the boiler and "
                  f"self-provision failed: {str(e)[:60]}")
            return
    # NO electric poles: pump->boiler->engine needs none, and poles need
    # copper we don't mine in this stage
    for proto, qty in [(Prototype.OffshorePump, 1), (Prototype.Boiler, 1),
                       (Prototype.SteamEngine, 2), (Prototype.Pipe, 10)]:
        if inv_count(proto) >= qty:
            continue
        try:
            _b(craft_item, proto, qty)
        except Exception as e:
            print(f"craft fail {proto}: {str(e)[:70]}")
    print(inspect_inventory())

def sk_power_build():
    """Power quantum 2: the water trek + placement chain. The ONLY long walk
    in the power path, so a pathfinder wedge costs just this quantum."""
    print("SKILL power_build")
    if not (inv_count(Prototype.OffshorePump)
            and inv_count(Prototype.Boiler)
            and inv_count(Prototype.SteamEngine)):
        print("BLOCKED power_build: parts missing — run power_craft first "
              f"(pump={inv_count(Prototype.OffshorePump)} "
              f"boiler={inv_count(Prototype.Boiler)} "
              f"engines={inv_count(Prototype.SteamEngine)}).")
        return
    water = nearest(_res("water"))
    pump = None
    for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1),(2,0),(-2,0),(0,2),(0,-2)]:
        for d in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT):
            try:
                p = Position(x=water.x + dx, y=water.y + dy)
                try:
                    _b(move_to, Position(x=p.x, y=p.y - 3))
                except Exception:
                    pass
                pump = _b(place_entity, Prototype.OffshorePump, position=p, direction=d)
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
        # step aside before building the chain — never stand where the
        # boiler/engines will land (embedded character = wedged walk queue)
        _b(move_to, Position(x=pump.position.x + 5, y=pump.position.y - 5))
    except Exception:
        pass
    try:
        boiler = _b(place_entity_next_to, Prototype.Boiler, pump.position,
                                      Direction.UP, spacing=2)
        _fuel(boiler, 20)
        _b(connect_entities, pump, boiler, Prototype.Pipe)
        prev = boiler
        engines = 0
        for _ in range(2):
            eng = None
            for d in (Direction.UP, Direction.RIGHT, Direction.LEFT, Direction.DOWN):
                try:
                    eng = _b(place_entity_next_to, Prototype.SteamEngine,
                                               prev.position, d, spacing=2)
                    _b(connect_entities, prev, eng, Prototype.Pipe)
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
        _b(craft_item, Prototype.StoneFurnace, n)
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
                _touch(insert_item, Prototype.Coal, f, quantity=8)
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
        made = _b(craft_item, proto, n)
        print(f"crafted {made}")
    except Exception as e:
        print("craft fail:", str(e)[:100])
    print(inspect_inventory())

def sk_keep_fed(radius=150):
    acts = []
    if inv_count(Prototype.Coal) < 15:
        try:
            p = nearest(_res("coal"))
            _b(move_to, p)
            _hv( p, 60)
            acts.append("mined 60 coal")
        except Exception as e:
            acts.append("coal restock fail " + str(e)[:40])
            try:
                w = nearest(_res("wood"))
                _b(move_to, w)
                _hv(w, 12)
                acts.append("coal unreachable -> chopped 12 wood for fuel")
            except Exception as e2:
                acts.append("wood fallback fail " + str(e2)[:40])
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
                if (round(e.position.x), round(e.position.y)) in collectors:
                    try:
                        got = _touch(extract_item, Prototype.Coal, e, quantity=50)
                        if got:
                            swept += 1
                    except Exception:
                        pass
                    continue
                try:
                    _fuel(e, 4)
                    fueled += 1
                except Exception:
                    pass
                for proto in (Prototype.IronPlate, Prototype.CopperPlate):
                    try:
                        got = _touch(extract_item, proto, e, quantity=50)
                        if got:
                            swept += 1
                    except Exception:
                        pass
                if inv_count(Prototype.IronOre) > 40:
                    try:
                        _touch(insert_item, Prototype.IronOre, e, quantity=15)
                    except Exception:
                        pass
            elif nm in ("burner-mining-drill", "boiler", "burner-inserter"):
                try:
                    _fuel(e, 4)
                    fueled += 1
                except Exception:
                    pass
        except Exception:
            pass
    print(f"keep_fed: fueled={fueled} swept={swept} {' | '.join(acts)}")
    print(inspect_inventory())

def sk_lab():
    """Craft + place a lab wired to the steam engine (WR-PACE §3: makes
    power_gen and research scoreable). Needs ~35 iron + ~15 copper plates —
    run a copper mine_line first; keep_fed sweeps copper plates."""
    print("SKILL lab")
    fe = inv_count(Prototype.IronPlate)
    cu = inv_count(Prototype.CopperPlate)
    if fe < 30 or cu < 15:
        print(f"BLOCKED lab: need ~30 iron + ~15 copper plates (have "
              f"{fe} iron / {cu} copper). mine_line copper + keep_fed first.")
        return
    try:
        ents = get_entities(radius=200)
    except Exception:
        ents = []
    eng = None
    for e in ents:
        if e.name == "steam-engine":
            eng = e
            break
    if eng is None:
        print("BLOCKED lab: no steam engine built — power_build first.")
        return
    for proto, qty in [(Prototype.ElectronicCircuit, 10),
                       (Prototype.IronGearWheel, 10),
                       (Prototype.TransportBelt, 4),
                       (Prototype.Lab, 1)]:
        if inv_count(proto) >= qty:
            continue
        try:
            _b(craft_item, proto, qty)
        except Exception as e:
            print(f"craft fail {proto}: {str(e)[:70]}")
    if not inv_count(Prototype.Lab):
        print("lab craft failed — check plate counts above")
        return
    if inv_count(Prototype.SmallElectricPole) < 2:
        try:
            w = nearest(_res("wood"))
            _b(move_to, w)
            _hv(w, 2)
            _b(craft_item, Prototype.SmallElectricPole, 2)
        except Exception as e:
            print("pole prep fail:", str(e)[:70])
    lab = try_place(Prototype.Lab,
                    Position(x=eng.position.x + 6, y=eng.position.y))
    if lab is None:
        print("lab placement failed near engine")
        return
    for frac in (0.4, 0.75):
        px = eng.position.x + (lab.position.x - eng.position.x) * frac
        py = eng.position.y + (lab.position.y - eng.position.y) * frac
        try_place(Prototype.SmallElectricPole, Position(x=px, y=py), sweep=8)
    print(f"lab at {lab.position} — queue research next")

def sk_research(tech="Automation"):
    """Start researching (a legal player action — it's a button click)."""
    print(f"SKILL research {tech}")
    t = getattr(Technology, tech, None)
    if t is None:
        print(f"unknown technology {tech}")
        return
    try:
        ing = _b(set_research, t)
        print(f"research started: {tech} (needs {str(ing)[:80]})")
    except Exception as e:
        print("research fail:", str(e)[:90])

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
    # ground truth the brain can't argue with (batch-6: a brain declared
    # "power online" while power_craft sat BLOCKED, then chased copper)
    plates = inv_count(Prototype.IronPlate)
    power = bool(ents.get("boiler") and ents.get("steam-engine"))
    print(f"CHECKLIST (game truth): power_built={'YES' if power else 'NO'}"
          f" | drills_placed={ents.get('burner-mining-drill', 0)}"
          f" | furnaces={ents.get('stone-furnace', 0)}"
          f" | iron_plates_in_hand={plates}")
    print(f"AFFORD NOW: mine_line drills craftable={plates // 9}"
          f" | power_craft={'YES' if plates >= 30 else 'NO (need %d more plates)' % (30 - plates)}")

print("PRELUDE LOADED — skills:", [k for k in dir() if k.startswith("sk_")])
'''

# S1 pace card distilled from the Strategy Bible (STRATEGY.md). Written into
# each brained lane's workdir CLAUDE.md — the claude CLI auto-loads it, so
# every brain "reads the bible". Route facts only, no recipe trivia (field
# finding: wiki knowledge alone never helped; pacing + doctrine do).
BIBLE_CARD = """# S1 pace card — distilled from S1-BIBLE.md (numbers are env-verified)

WR yardstick: Power 4:31 (with ~35-40 drills, lab placed, Automation running).

COSTS (iron plates unless noted): drill+drop-furnace PAIR = 9 Fe + 10 stone.
Power pack = 83 Fe (pump 7, boiler 4, engine 31 EACH, pipes) + 10 stone;
1-engine minimum = 52 Fe. Lab = 42 Fe + 15 Cu. Automation = 10 packs
(2 Fe + 1 Cu each, 5s craft). One engine powers 15 labs — build the second
engine only when electric drills are coming.

INCOME: a pair yields 0.25 plates/s forever; it repays its 9 Fe in ~40s and
beats hand-mining (0.5 ore/s, occupies you) after just 30s of runtime.
Marginal pairs: 1-6 return 3-8x by 5:00; 7-8 pay if placed before ~3:10;
9+ pay only past the window — in a real match KEEP placing them.
COAL: each pair burns ~3.6 coal/min — 1 coal pair per 4 other pairs, placed
BEFORE the fleet starves.

ROCKS: a huge rock = 24-50 stone AND 24-50 coal in 3s of mining (~50x
faster than hand-mining, fully legal). Check for rocks near the route
before committing to a stone-patch trip.

ROUTE SHAPE (5-min window): rocks/stone first errand -> hand-mine ~26 iron
while crafting furnaces -> 2 bootstrap furnaces + first pairs by ~1:45 ->
6 iron pairs + 1 coal pair by ~2:45 -> bank 52+ Fe -> power ~3:45 ->
2 copper pairs -> 10 green circuits -> lab -> Automation by 5:00.

DOCTRINE: drills before power (economy funds the trophy, never the
reverse). Batch errands by geography, not resource. Keep the craft queue
full — walking time is crafting time. Banked plates make builds one-shot.
"""

# ---------------------------------------------------------- controller ------
SKILLS = {  # name -> (timeout_s, allowed arg keys)
    # timeouts sized for legal-player mode (fast=False): walking between
    # patches and real craft times make every skill several times slower.
    # Short stage sprints should cap these via cfg "timeout_cap" — one hung
    # skill ate 428s of a 300s stage window in s1-batch2.
    "gather":          (280, {"stone", "coal", "iron", "copper"}),
    "bootstrap_place": (150, set()),
    "bootstrap_feed":  (120, set()),
    "mine_line":       (340, {"resource", "n"}),
    "power_craft":     (120, set()),
    "power_build":     (240, set()),
    "lab":             (240, set()),
    "research":        (60, {"tech"}),
    "expand_smelting": (280, {"n"}),
    "craft":           (220, {"item", "n"}),
    "keep_fed":        (280, {"radius"}),
}

DEFAULT_PLAN = [
    # per-resource gather quanta: a pathfinder wedge costs one 90s slot,
    # not the whole shopping trip
    {"skill": "gather", "args": {"iron": 30, "coal": 25}},
    {"skill": "gather", "args": {"stone": 22}},
    {"skill": "bootstrap_place", "args": {}},
    {"skill": "bootstrap_feed", "args": {}},
    {"skill": "gather", "args": {"iron": 40, "coal": 20}},
    {"skill": "keep_fed", "args": {}},
    {"skill": "gather", "args": {"stone": 15}},
    {"skill": "mine_line", "args": {"resource": "iron", "n": 2}},
    {"skill": "keep_fed", "args": {}},
    {"skill": "power_craft", "args": {}},
    {"skill": "power_build", "args": {}},
]

CATALOG = """You are the STRATEGY BRAIN for a Factorio agent. You never write
game code — a reliable scripted autopilot executes SKILLS; you choose and
order them. Between your decisions the autopilot constantly runs keep_fed
(refuels every burner, sweeps finished plates out of furnaces, feeds spare
ore in, restocks coal by hand-mining) — so build maintenance is FREE. Your
job is expansion strategy: what to build next, how much, in what order.

SKILL CATALOG (args -> effect, rough prerequisites):
- gather {stone,coal,iron,copper}: hand-mine raw resources. Fast. No prereqs.
- bootstrap_place {}: craft 3 stone furnaces (self-gathers missing inputs)
  and place 2 at the iron patch. Follow with bootstrap_feed.
- bootstrap_feed {}: load nearby furnaces with coal + iron ore from your
  inventory. keep_fed sweeps the finished plates out automatically.
- mine_line {resource: iron|copper|coal|stone, n}: place n burner drills,
  each with a drop-feed furnace — a self-running mine+smelt line. Auto-crafts
  drills/furnaces first: needs ~9 iron plates + ~10 stone per drill.
  A coal mine_line's furnaces act as coal collectors the autopilot empties.
- power_craft {}: craft pump + boiler + 2 steam engines + pipes near base.
  Needs ~35 iron plates banked. Run before power_build.
- power_build {}: walk to water and place pump->boiler->engines, piped and
  coaled. Needs the parts from power_craft in inventory.
- lab {}: craft green circuits + a lab, place it wired to the steam engine.
  Needs ~30 iron + ~15 copper plates (mine_line copper feeds copper).
- research {tech}: start researching (default "Automation"). Needs the lab.
RULE: a skill that prints BLOCKED is missing a prerequisite — queue the fix
(smelt plates, gather stone), NOT the same skill again; immediate re-queues
of a blocked skill are auto-deferred for 40s.
RULE: the CHECKLIST line in your status is GAME TRUTH. Nothing is built
until the checklist says so — queueing a skill does not mean it succeeded.
Use the AFFORD line to time your builds instead of guessing.
RULE: DRILLS FIRST. Drills are the only ore income — a furnace without a
drill feeding it is dead weight, and plate production flatlines without
drills (measured: lanes that built furnaces before drills froze at 30
plates). Sequence: bootstrap -> drills -> more furnaces -> power.
RULE: BATCH BIG. If the AFFORD line says 6 drills are craftable, order 6 —
timid n=2 mine lines lose to a novice human hand-placing 15 (measured,
live match). The skill caps itself to what's affordable; you never need
to under-ask.
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
re-consulted with fresh status every ~90 seconds while the autopilot works.
BE TERSE: note under 15 words, no prose, no reasoning outside the JSON —
long replies delay your own next decision."""


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
    # script_only: no LLM anywhere — execute default_plan then keep_fed.
    # This is the route-search mode (WR-PACE §1/§2): the route is optimized
    # offline; brains are for divergence and novel seeds.
    script_only = bool(cfg.get("script_only"))
    catalog = CATALOG.replace(
        "every ~90 seconds",
        f"every ~{cfg.get('plan_every_s', 90)} seconds")
    system = (catalog + "\n\n" + cfg.get("persona", "")
              + "\n\nMATCH CONTEXT:\n" + shared_goal)
    brain = None if script_only else brain_cls(
        name, cfg["model"], cfg["accounts"], system)
    if brain is not None and getattr(brain, "workdir", None):
        try:  # the claude CLI auto-loads workdir CLAUDE.md: bible in context
            (brain.workdir / "CLAUDE.md").write_text(BIBLE_CARD)
        except Exception:
            pass

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

    state = {"queue": list(cfg.get("default_plan") or DEFAULT_PLAN),
             "inflight": False, "last_plan": 0.0}
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
        pace = cfg.get("pace_oracle")
        pace_line = f"\nPACE ORACLE:\n{pace}\n" if pace else ""
        return (f"STATUS at minute {(time.time() - t0) / 60:.1f} "
                f"(production score {score}):{pace_line}\n{str(st)[:1200]}\n"
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
    blocked_at = {}  # skill -> time it last printed BLOCKED
    for step in range(1, max_steps + 1):
        with lock:
            item = state["queue"].pop(0) if state["queue"] else None
        if item is None:
            item = {"skill": "keep_fed",
                    "args": ({"radius": cfg["sweep_radius"]}
                             if cfg.get("sweep_radius") else {})}
        # BLOCKED cooldown: a skill that just reported a missing prerequisite
        # gets deferred instead of spam-retried (batch-4: brains re-queued
        # power 3-4x while plates smelted). Skip to the next runnable queue
        # item (WR-PACE §4) — only fall back to keep_fed if nothing runs.
        deferred = []
        while item and time.time() - blocked_at.get(item["skill"], 0) < 40:
            deferred.append(item)
            with lock:
                item = state["queue"].pop(0) if state["queue"] else None
        if deferred:
            log(name, "defer",
                f"deferred {[d['skill'] for d in deferred]} (BLOCKED cooldown)"
                f" -> running {item['skill'] if item else 'keep_fed'}")
            with lock:
                state["queue"].extend(deferred)  # retry later, order kept
        if item is None:
            item = {"skill": "keep_fed",
                    "args": ({"radius": cfg["sweep_radius"]}
                             if cfg.get("sweep_radius") else {})}
        inv = _invocation(item)
        code = inv if not inline_prelude else PRELUDE + "\n" + inv
        timeout = min(SKILLS[item["skill"]][0],
                      cfg.get("timeout_cap") or 10 ** 6)
        log(name, "code", inv)
        try:
            score, _, result = instance.eval(code, agent_idx=idx,
                                             timeout=timeout)
        except Exception as e:
            score, result = None, f"eval error: {e}"
        last_result = str(result)
        log(name, "result", last_result)
        if "BLOCKED" in last_result:
            blocked_at[item["skill"]] = time.time()
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
        # idle no-op detection: an empty queue + a keep_fed that found nothing
        # to do means the body is spinning — back off and replan NOW instead
        # of burning eval spam (batch-1 failure mode: 130 no-op sweeps)
        idle_noop = (item["skill"] == "keep_fed"
                     and "fueled=0 swept=0" in last_result)
        due = time.time() - state["last_plan"] > cfg.get("plan_every_s", 90)
        if (not script_only and not state["inflight"]
                and (due or (idle_noop
                             and time.time() - state["last_plan"] > 10))):
            plan_async(build_status(last_result, score))
        # wall-clock sleeps cost speed× game time at lab speeds — scale them
        # so high-speed route evals aren't biased toward fewer-bigger quanta.
        # Base inter-quantum sleep cut 1 -> 0.2s (needle audit: per-quantum
        # overhead is a top-3 component of the human's 3x live-match edge).
        wscale = float(cfg.get("wall_sleep_scale") or 1)
        time.sleep((6 if idle_noop else 0.2) * wscale)
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
