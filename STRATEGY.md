# STRATEGY.md — the Factorio Strategy Bible (2026-07-19)

Pure Factorio strategy — no AI anywhere in this document. This is the
ground-truth reference for how expert humans play the game: **how they divide
it into phases, the exact numbers they build to, the routes they follow, and
how they measure success.** Compiled from speedrun.com leaderboards + rules,
Nefrums' Any% guide and split file, Phredward/AntiElitz's Default Settings
guide, Zaspar's WR VOD (LiveSplit overlay read frame-by-frame), the TAS repos,
the official wiki, Kirk McDonald/factoriolab calculator internals, and the
community's canonical guides (KatherineOfSky, Nilaus, the forums). Sources
inline. Version note: **our environment is Factorio 2.0** (FLE v0.4) — 2.0
deltas are flagged wherever they break a classic 1.1 number (§2.8).

---

## 1. How experts divide the game — the phase model

### 1.1 The speedrun decomposition (what the WR actually splits on)

Zaspar's Any% world record (**1:18:56**, v1.1.109, chosen seed, biters off —
[speedrun.com run z1945rwm](https://www.speedrun.com/factorio/runs/z1945rwm))
uses build/location-based splits. Read directly from the WR VOD's LiveSplit
overlay:

| # | Phase (split) | Cum. time | What the phase delivers |
|---|---|---|---|
| 1 | **Power** | 4:31 | Burner mining running; powerplant + first lab placed; Automation researching |
| 2 | **Intermediates** | 14:10 | Half iron smelting lane; gears/belts/green-circuits automated; first electric miners |
| 3 | **Labs** | 17:26 | 9 red + 10 green science assemblers, ~30 labs |
| 4 | **Steel Furnaces** | 22:09 | Steel + brick smelting columns |
| 5 | **Power 2** | 23:58 | Second (20-boiler-class) powerplant |
| 6 | **Blue mall** | 29:37 | Mall + oil/refinery infrastructure |
| 7 | **Blue Science** | 34:23 | Chemical science automated |
| 8 | **Box** | 36:02 | Robot-frame buffer / bots prep |
| 9 | **Go to Mixed** | 43:36 | Bots online; big smelting/mining blueprinted |
| 10 | **Mixed** | 51:21 | Mixed-belt circuit + science mega-build |
| 11 | **High Tier Science** | 1:02:20 | Purple + yellow science flowing |
| 12 | **Launch** | **1:18:56** | Silo + 4× prod-3 modules, rocket parts, launch |

Research-completion checkpoints from the same run (the alternative split
convention used by the community auto-splitter): Automation done ≈ 6:13,
Logistics done ≈ 14:56 — consistent with our older WR split table.

**Phase boundaries are *build events*, not research events**, in top runners'
own splits — "the factory can now do X" (first powerplant, science automated,
bots online), with research completions as secondary checkpoints.

### 1.2 The teaching decomposition (Nefrums' 32 segments)

Nefrums' beginner split file breaks the same run into finer segments — this is
the most granular expert phase model that exists
([guide](https://www.speedrun.com/factorio/guides/jg8lg)):

> Burner City · Power · Automation Science · Power +4 · Full Iron · Half
> Copper · Electronic Circuits · Power +5 · Green/Red Science · Labs ×30 ·
> Mall · Steel + Bricks · Power +20 · Advanced Circuits · Chemical Science ·
> Batteries · Engines and Frames · **Bots** · Power Overwhelming (+60) ·
> Smelting · Big Green · Big Oil (24) · Big Reds (60) · Modules (8 Speed/8
> Prod) · Processing Units · Production Science · Low Density Structures ·
> Utility Science · Rocket Fuel · Rocket Control Units · Silo Research ·
> Rocket Launch

Note the structural rhythm: **every few phases is a Power phase** (power
capacity is re-provisioned ahead of each scale-up), and **"Bots" is the hinge
of the whole run** — before it you build by hand, after it you build by
blueprint.

### 1.3 The casual-progression phase model (non-speedrun)

The community's consensus base-lifecycle
([forums t=89392](https://forums.factorio.com/viewtopic.php?t=89392), KoS
"Entry Level to Megabase"):

1. **Bootstrap/starter base** — 5–20 assemblers making belts, inserters,
   gears, circuits, ammo + red/green science. Explicitly temporary: "the base
   that builds the base." Ends when construction bots + a personal roboport
   exist.
2. **Bus base (the transition factory)** — main-bus architecture; carries you
   through oil, blue/purple/yellow science, and the first rocket. Breaks at
   roughly the 1-rocket-to-low-hundreds-SPM band.
3. **Megabase** — train/city-block architecture, scaled per-product modules.
   Constraint shifts from layout to UPS (CPU).

Typical wall-clock milestones for a normal expert-but-not-speedrun 1.x game:
red science automated by ~hour 1–2, green + trains hour 2–4, oil/blue hour 4–8
("the first major complexity spike — three fluid outputs at once"), first
rocket ~15–20h experienced / 24–48h typical first playthrough
([forums t=62732](https://forums.factorio.com/viewtopic.php?t=62732)).

### 1.4 First hour of the WR, sampled (our benchmark window)

From VOD frames of the 1:18:56 run (run-time):

| Minute | State of the factory |
|---|---|
| 0–4:31 | Burner phase: mining rocks, ~35–40 burner miners hand-placed, trees chopped (~200 wood funds the run's belts/poles); powerplant + lab down at 4:31 |
| 5:00 | Automation research 27% |
| 10:00 | Logistics queued; ~10 **electric** drills going down on copper; burner iron/stone rows feeding stone-furnace columns; assembler-made belts already |
| 14:10–17:26 | Intermediates automated → 9 red + 10 green science + ~30 labs live |
| 20:00 | Fast Inserter done; steel/brick furnace columns being placed |
| 30:00 | Mall + oil done; Plastics research 48%; mass-placing electric drills; refinery column running |
| 34:23 | Blue science automated |
| 45:00 | Logistics 2 done; **LDS research started**; 45×7 drill-row blueprint being pasted by construction bots |
| 51:21 | Mixed mega-build complete (big green + big red + blue chips on shared belts) |
| 60:00 | Rocket Fuel research 69%; purple + yellow science area live |

**This table is the pace oracle for a 60-minute benchmark run**: at minute 60
a WR-pace factory has all six sciences flowing and is researching rocket fuel.

---

## 2. The numbers — canonical ratios and limits

The "you need N of X per M of Y" catalog. All headline numbers verified
against the wiki; ratios assume same-tier machines (speeds cancel — that's
why the ratios are integers). Full derivations: Kirk McDonald's
["Calculating Factorio"](https://kirkmcdonald.github.io/posts/calculation.html).

### 2.1 Mining → smelting chain

| Fact | Number | Source |
|---|---|---|
| Burner drill | 0.25 ore/s (≈7 ore per coal) | [wiki](https://wiki.factorio.com/Burner_mining_drill) |
| Electric drill | 0.5 ore/s | [wiki](https://wiki.factorio.com/Electric_mining_drill) |
| Stone furnace | 0.3125 plates/s (3.2 s smelt, speed 1) | [wiki](https://wiki.factorio.com/Stone_furnace) |
| Steel/electric furnace | 0.625 plates/s (speed 2) | wiki |
| **Drills : furnaces** | 1 electric drill feeds 1.6 stone furnaces (5:8) or 0.8 steel furnaces (5:4) | derived |
| **Furnaces per yellow belt of plates** | **48 stone** or **24 steel/electric** | classic column math |
| Drills per belt of ore | 30 electric (60 burner) per yellow belt; 90 electric per blue | derived |
| Steel | 5 plates → 1 steel, but time cancels: **1 iron furnace feeds exactly 1 steel furnace** same-tier; 120 steel furnaces per yellow belt of steel | derived |

The 48-stone column is the consensus blueprint **because it upgrades in place**:
stone→steel furnaces and yellow→red belts are both exactly 2×, so the same
layout serves two game phases with zero re-routing.

### 2.2 Power

| Fact | Number | Source |
|---|---|---|
| **Pump : boiler : engine (2.0)** | **1 : 200 : 400** (pump 1200 water/s; boiler 6 water/s → 60 steam/s; engine 30 steam/s) | [wiki](https://wiki.factorio.com/Boiler) |
| 1.1 legacy | 1 : 20 : 40 — the most famous ratio 2.0 broke (1 water → 10 steam now) | wiki changelog |
| Steam engine | **900 kW**; 1 boiler : 2 engines = 1.8 MW block (unchanged) | [wiki](https://wiki.factorio.com/Steam_engine) |
| Coal per boiler | 0.45 coal/s (1.8 MW ÷ 4 MJ) — a 20-boiler row eats 9 coal/s = **18 electric coal miners** | derived |
| Solar : accumulator | 0.84 acc/panel (exact 2646:3125); 23.8 panels per MW of average load; panel avg 42 kW | [wiki](https://wiki.factorio.com/Solar_panel) |

### 2.3 Science packs (recipes + the equal-rate assembler set)

| Pack | Recipe | Time → out | Rate/asm (speed 1) |
|---|---|---|---|
| Red | 1 copper plate + 1 gear | 5 s → 1 | 0.2/s |
| Green | 1 belt + 1 inserter | 6 s → 1 | 0.167/s |
| Military | 1 piercing mag + 1 grenade + 2 walls | 10 s → **2** | 0.2/s |
| Blue | 1 sulfur + 3 red circuits + 2 engine units | 24 s → **2** | 0.083/s |
| Purple | 30 rails + 1 electric furnace + 1 prod module | 21 s → **3** | 0.143/s |
| Yellow | 2 blue chips + 1 robot frame + 3 LDS | 21 s → **3** | 0.143/s |

- **Equal-SPM assembler set: 5 red : 6 green : 5 military : 12 blue : 7
  purple : 7 yellow** — exactly equal pack rates at any shared tier. With
  assembler-2s this set = **45 SPM** (the classic "starter base" size); with
  assembler-3s = 75 SPM. ([cheat sheet](https://factoriocheatsheet.com/))
- Sub-ratios: **1 gear assembler feeds 10 red-science assemblers** (the
  oft-quoted "0.775" figure is apocryphal — exact math is 1:10).
- **Labs**: 1 lab ≈ 1 SPM on 60-second techs (2 SPM on 30 s techs) → 45 SPM
  needs ~45–90 unmoduled labs. ([wiki](https://wiki.factorio.com/Lab))
- Raw cost per pack (wiki totals): red 2 Fe + 1 Cu · green 5.5 Fe + 1.5 Cu ·
  blue 12 Fe + 7.5 Cu + 38.5 crude · purple 52.5 Fe + 19.2 Cu + 11.7 stone ·
  yellow 33.3 Fe + 49.8 Cu + 106.8 crude.

### 2.4 Intermediates

| Product | Recipe | Canonical ratio |
|---|---|---|
| **Green circuit** | 1 iron + 3 cables, 0.5 s | **3 cable asm : 2 circuit asm** (the famous 3:2 block) |
| Red circuit | 2 GC + 4 cables + 2 plastic, 6 s | 1 cable asm : 6 red asm; 1 GC asm : 6 red asm; 1 plastic chem plant : 6 red asm |
| Blue chip | 20 GC + 2 RC + 5 acid, 10 s | 20 GC each — the dominant GC sink late-game |
| Engine unit | 1 gear + 1 pipe + 2 steel, 10 s | 10 engine asm : 12 blue-science asm |
| Copper cable / gears | make **at point of use**, never bussed (they expand: 1 plate → 2 cables; 2 plates → 1 gear) | main-bus doctrine |

### 2.5 Oil

- Basic: 100 crude → 45 petroleum (5 s). Advanced: 100 crude + 50 water → 25
  heavy + 45 light + 55 petroleum. Cracking: 40 heavy→30 light (2 s); 30
  light→20 petroleum (2 s). ([wiki](https://wiki.factorio.com/Oil_processing))
- **All-to-petroleum ratio: 20 refineries : 5 heavy-crack : 17 light-crack**
  (small build ≈ 4:1:4). Advanced + full cracking yields 0.925 petroleum per
  crude vs 0.45 basic — advanced oil is a 2× multiplier on every oil product.

### 2.6 Belts & inserters

- Belt throughput (per full belt, unchanged in 2.0): **yellow 15/s · red
  30/s · blue 45/s** (900/1800/2700 per min); Space Age turbo 60/s.
  ([wiki](https://wiki.factorio.com/Belt_transport_system))
- Inserters (chest-to-chest, base hand size): yellow ≈0.86/s, long ≈1.25/s,
  fast ≈2.5/s; with max capacity research: fast 10/s, bulk 30/s. Rule of
  thumb: any saturated feed needs **fast** inserters; train unloading needs
  bulk. 2.0 rename: 1.1 "stack inserter" → **bulk inserter**.

### 2.7 Rocket & SPM scaling

- **2.0 rocket part: 1 LDS + 1 blue chip + 1 rocket fuel** × 100 parts (50
  with Space Age) — the rocket is **~10× cheaper than 1.1** (which was 10 LDS
  + 10 RCU + 10 fuel per part; RCU no longer exists).
  ([wiki](https://wiki.factorio.com/Rocket_part))
- SPM scaling is linear in the per-pack raws: **45 SPM ≈ 5,000 iron + 3,580
  copper plates/min** (≈5.5 + 4 yellow belts of plates) and ≈1,200 green
  circuits/min. 60 SPM ≈ 6,660 Fe + 4,770 Cu/min. Generate exact tables with
  [Kirk McDonald](https://kirkmcdonald.github.io/) / [factoriolab](https://factoriolab.github.io/).

### 2.8 Factorio 1.1 → 2.0 checklist (our env is 2.0)

1. Boiler water: **1:20:40 → 1:200:400** (only the pump leg changed).
2. Rocket: ~10× cheaper; RCU deleted (blue chips instead); 100→50 parts in SA.
3. Inserter renames (stack→bulk); new SA stack inserter (belt stacking).
4. Unchanged: belt speeds, drill rates, furnace speeds/smelt times, all
   science recipes, the 3:2 circuit block, oil ratios, solar ratio.

---

## 3. The route — expert build orders

### 3.1 Nefrums' Any% route (the canonical teaching route)

From the full guide text ([speedrun.com/factorio/guides/jg8lg](https://www.speedrun.com/factorio/guides/jg8lg)):

**Burner phase counts: 10 iron / 6 copper / 16 coal / 4 stone burner drills.**
Mine the starting rocks first (free ore), chop trees while research runs
(~200 wood funds all early belts/poles), and *keep the handcrafting queue
full at all times* — walking time is crafting time.

**Order of automation** (each build "starts by adding more miners"):
1. Powerplant + 1 lab → research Automation; handcraft everything meanwhile.
2. First assemblers → **gears + belts automated first**, hand-fed half iron
   smelting lane; temporary hand-fed mini-science.
3. Green circuits (with an iron-overflow buffer) → then **inserters + miners
   automated**; chest-limit the gear chests.
4. +5 boilers → **9 red + 10 green science assemblers, 30 labs**; kill the
   mini-science.
5. Mall (second iron lane; gears+GC share a belt; chest limits 1–4 slots).
6. Steel + bricks: 15 miners each; **double input belts on steel columns** so
   the same build survives the stone→steel furnace upgrade; upgrade key
   assemblers to tier 2.
7. Third powerplant: standard 20-boiler block, 18 coal miners.
8. Red circuits: **8 refineries + 3 plastics + 18 red-circuit assemblers**
   (feeders: 7 GC + 3 wire assemblers).
9. Blue science: sulfur + red circuits mixed on one belt; first-oil tank
   plan: 2 petroleum, 8 light, 1 heavy.
10. **Bots** (the hinge): engines → frames (chest-limited) → roboport; mall
    chests flip to provider chests; bots take over building and even
    wood-gathering.
11. Copy-paste era: powerplants ×4 (~80 boilers); +2 steel and +5 ore
    smelting columns by blueprint (each ore column = a full belt = 30 miners).
12. Big green (prod-1s in circuit assemblers) → **big oil: 24 refineries** →
    **big red: 60 red-circuit assemblers** → modules (8 prod + 8 speed asm)
    → **28 blue-chip assemblers** → purple (direct-fed) → **40 LDS
    assemblers** → yellow (hand-feed 25 frames per assembler) → **40 rocket
    fuel + 64 RCU assemblers** → 4 prod-3 into the silo → hand-feed the silo
    (inserters can't keep up) → launch.

**Fixed core research order**: Automation → Logistics → Electronics → Fast
Inserter → Logistic Science → Steel → Automation 2 → Engine → Fluid Handling
→ Oil → Plastics → Adv. Electronics → Sulfur → Chemical Science → Battery →
Modules/Prod-1 → Adv. Oil → Lubricant → Electric Engines → Robotics →
**Construction Robots** → Adv. Electronics 2 → Production Science → LDS →
Utility Science → Rocket Fuel → Speed/Prod 2-3 → RCU → Rocket Silo.

**Buffer doctrine** (explicit in the guide): buffers are *required* for
stone/bricks, every steel build, red circuits, robot frames, chem/prod/
utility science, blue chips, modules, LDS, RCU, and rocket fuel — banked
intermediates are what make the endgame hand-feeds possible.

### 3.2 AntiElitz/Phredward Default Settings deltas (biters on, random map)

([guide](https://www.speedrun.com/factorio/guides/li2kd)) Differences that
matter when the map is random and hostile:
- Map-picking is a skill with hard thresholds: starting iron **≥420K** (must
  support 80 miners), 40 on copper, oil ≥1600%; the base layout must work in
  all 4 rotations/mirrors.
- Slightly different burner counts (iron 7×2, copper 7, coal 6×2×2, stone 4);
  only 3 boilers initially; first 10 red science hand-crafted.
- **Combat is routed, not reactive**: turrets → grenades → car + landmines
  (500 steel = 2,000 mines); Military 1-2 and walls sit in the research order.
- A deliberate **research pause** after Automobilism until prod-1 modules are
  in all labs — packs are too expensive to spend un-multiplied.
- Endgame counts: 13–14 refineries, 29 red-circuit assemblers, 42 labs, 11
  green/10 red science, iron outpost = 120 miners → 4 belts; circuit-network
  alarms flip module assemblers from prod→speed at exactly 500 prod-1s.

### 3.3 What the TAS proves (the mathematical ceiling)

- gotyoke's scripted Any% TAS: **1:21:20** on 0.18 — ~35,000 ordered actions,
  **zero robots** (perfect movement/craft interleaving beats bot overhead),
  crafting queue never idle. Its own retro flags under-buffered early steel
  (3–5 min loss) and a red-circuit shortage as its biggest errors.
- **Zaspar's 2026 TAS: 57:21** — first sub-hour
  ([video](https://www.youtube.com/watch?v=fkmRd5uJoKI)); dev commentary
  credits "maximizing early-game iron economy" and machine-precise assembler
  scheduling. TAS-vs-human gap on Any%: 1:18:56 → 57:21 (~27%) — that's the
  total value of perfect execution over the best human.
- Takeaway ranking of what time actually comes from: **early iron economy >
  never-idle crafting/research > buffer discipline > perfect placement**.

---

## 4. How success is measured

### 4.1 SPM — the universal metric

- **SPM = science packs per minute, per type, all types sustained
  simultaneously** — a base making 1k red but 400 yellow is a 400 SPM base.
  ([wiki glossary](https://wiki.factorio.com/Glossary))
- **The semi-official measurement protocol** (DaveMcW,
  [forums t=97410](https://forums.factorio.com/viewtopic.php?t=97410)):
  produce all 7 packs **while researching an infinite technology that
  consumes every pack** (Follower Robot Count), and measure **consumption
  over ≥10 minutes (better 1 hour)**. Consumption-side, because production
  can fill buffers and lie; long-window, because short windows sample noise.
- Tiers: **45 SPM** classic starter target · 60–100 common planning default ·
  **1,000 SPM = "megabase"** (wiki-canonized; where bus + basic trains stop
  working) · **10k+ = "gigabase"**. Alternative metrics that lost: rockets/min
  (megabase shorthand), power draw (skewed by module choice).
- 2.0 adds **eSPM** (effective SPM: includes productivity/biolab multipliers)
  — raw pack consumption understates research output in a moduled base.

### 4.2 The measurement instrument (production statistics)

- Per-force stats; windows **5s / 1m / 10m / 1h / 10h / 50h / 250h / 1000h**;
  the 5s and 1m windows are explicitly unreliable (small sample). API:
  `input_counts` = produced, `output_counts` = consumed; each precision level
  stores 300 samples. ([wiki](https://wiki.factorio.com/Production_statistics))
- Gotcha: consumption stats ignore productivity bonuses — lab prod modules
  make research progress exceed measured pack consumption.

### 4.3 Benchmark methodology (how the community tests a design)

The canonical shape of a Factorio design benchmark
([mulark.github.io](https://mulark.github.io/), forums UPS challenges):
1. **Fixed inputs** — editor-spawned ore/infinity chests, pinned mining
   productivity, standardized power source.
2. **Contracted sustained output** — "1 full blue belt, no gaps, for 1 hour";
   a single gap after ramp-up disqualifies.
3. **Measured cost at scale** — clone the design ×100 and benchmark
   `factorio --benchmark map.zip --benchmark-ticks N` on headless (run-to-run
   variance <0.1%); report min ms/tick.
Principles worth internalizing: normalize on output, compare cost; sustained
beats peak; re-benchmark instead of trusting inherited folklore (engine
optimizations have invalidated old rules more than once).

### 4.4 Calibration: how good is "good"? (Steam global achievements)

- **23.9%** of players ever launch a rocket ("Smoke me a kipper").
- Win under 15 hours: **4.9%**. Under 8 hours: **3.1%**. Lazy Bastard (≤111
  handcrafts): 3.8%. ([Steam stats](https://steamcommunity.com/stats/427520/achievements))
- First-launch time consensus: 60–120h true beginner · 24–48h typical · 15–20h
  experienced · ~1.5h speedrun-routed. The 15h/8h achievements are the
  closest thing to calibrated skill tiers the game has.

### 4.5 Bottleneck-finding doctrine (how experts debug a factory)

1. **Backed-up vs starved**: full-and-stopped = downstream of the problem;
   empty/starved = downstream of the *bottleneck* — walk upstream from
   starvation until you find the full input. Backpressure (stopped machines
   behind a full belt) is normal, not a fault.
2. **Graph-shape reading**: production sagging toward consumption =
   supply-bound; both flat and pinned = throughput ceiling; sawtooth =
   intermittent starvation (trains, power dips). Power satisfaction <100%
   slows *everything* proportionally — check it first.
3. **Theoretical vs observed**: compute the max rate of a machine group
   (rate = machines × speed ÷ recipe time), compare with the stats window;
   the gap localizes the bottleneck. (Max Rate Calculator / Rate Calculator
   mods do exactly this in-game.)
4. **Reallocation test**: temporarily give 100% of a contested resource to one
   consumer chain to expose whether the true limit is machines or raw supply.

---

## 5. Doctrine — the rules experts repeat

### 5.1 Priority rules
1. **The factory must grow** — iron demand never saturates; every build
   starts by adding miners (Nefrums' route rule).
2. **Automate anything you craft repeatedly**; hand-craft only one-offs and
   deadlock-breakers. The game's hand-craft friction is a designed nudge.
3. **Build the mall early**, chest-limit everything (unlimited mall chests
   will eat the base).
4. **Never let labs idle** — labs are cheap; add until the last one stutters.
5. **Power ahead of demand, never buffer instead of generating** — steam
   tanks mask a deficit until the collapse is unrecoverable (the ~30% power
   death spiral).
6. **Throughput over elegance early** — over-build and let machines idle;
   ratios are for when inputs are scarce, not for the first hour.
7. **Belts in multiples of 4 with gaps**; don't widen the bus later —
   re-inject fresh smelting mid-bus instead.
8. **Buffer before big builds** (Nefrums): banked intermediates are what let
   you erect a whole production block at once instead of drip-building.
9. **Military scales with pollution, not time** — evolution drivers: time
   +0.000004/s, pollution +0.0000153 per 1k units *produced* (absorption
   doesn't help), **spawner kill +0.002 each** (the strongest driver). Automate
   ammo before medium biters (~0.2 evolution).

### 5.2 Architecture selection
- **Bootstrap base** → ends at construction bots. **Main bus** (4 iron + 4
  copper + 2 GC lanes minimum; cables/gears made at point of use) → carries
  through first rocket. **City blocks** (100×100 grid, rails on perimeter,
  train limits for graceful degradation) → megabase. Don't torch the old
  base: build the next one beside it while it keeps producing, then
  cannibalize.

### 5.3 Failure-mode catalog (what kills factories)
1. **Coal/power death spiral** (coal miners lose power → boilers starve →
   less power) — dedicated self-feeding coal loop, generation surplus.
2. **Iron shortage cascade** — everything transitively needs iron; one
   starving belt propagates everywhere at once.
3. **Neglected military until evolution outruns you** — pollution keeps
   raising evolution even when absorbed.
4. **Lab/science imbalance** — packs piling up while research crawls (too few
   labs) or long lab daisy-chains starving the tail.
5. **Belt backpressure misreads** — a full belt is a buffer, not proof of
   throughput ("fake bus"); check input compression, not machine count.
6. **Averages lie at scale** — designs sized to mean throughput gridlock
   under variance; size for recovery, not average.

---

## 6. What this implies for a 60-minute scored run (measurement only)

Mapping the Bible onto our benchmark window (median automated score at 60
minutes, [SCORING.md](SCORING.md)):

- **Pace oracle**: §1.4 is the split table to grade against — power ~4:30,
  intermediates automated ~14, red+green science + 30 labs ~17:30, steel
  ~22, oil/mall ~30, blue science ~34:30. A run that hasn't automated red
  science by minute ~17 is off WR pace by definition.
- **Phase gates are build events** (first powerplant, science *assemblers*
  running, bots online) — matching how top runners split, and what
  `decisions.py` already timestamps.
- **Measure consumption, sustained, long-window** — the community's SPM
  protocol maps directly onto our automated-score metric: buffers and
  hand-crafting are exactly the "production-side lies" their protocol exists
  to exclude.
- **The route's first-hour numbers are the target counts**: 10/6/16/4 burner
  drills → 20-boiler power blocks (18 coal miners each) → 48-stone-furnace
  columns (double-belted for in-place upgrade) → 9 red + 10 green science
  assemblers + 30 labs → 15+15 steel/brick miners → 8 refineries + 3
  plastics + 18 red-circuit assemblers.
