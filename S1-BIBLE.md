# S1-BIBLE.md — the first five minutes, in numbers (2026-07-20)

The decision bible for Stage 1 (0:00–5:00, "Power"): every number a brain
needs to choose *what to build next and how many*, under **match physics**
(vanilla hand-mining rate, real walking, real craft times). All game
constants below were **ground-truthed against our own running environment
via read-only RCON** (not just the wiki) on 2026-07-20; map facts are for
lab seed 424242. Companion docs: STRATEGY.md (whole-game bible),
WR-PACE.md (doctrine), SEGMENTS.md (rubric).

Regenerate the empirical section: `uv run python bible_stats.py`.

---

## 1. Ground-truthed constants (our env, Factorio 2.0)

### Character (verified in-env)
| Fact | Value | Consequence |
|---|---|---|
| Hand-mining | 0.5 items/s (2 s/item) | 40 ore = 80 s of your life. Hand-mine only what bootstraps machines |
| Handcraft speed | 1× (gear 0.5 s, drill chain ≈ 4 s) | crafting is cheap; *acquiring plates* is the cost |
| Run speed | 0.15 tiles/tick ≈ **9 tiles/s** | walk cost in s ≈ distance ÷ 9; round trips double it |
| Reach | ~10 tiles (place/interact) | place from distance; never stand on the build spot |

### Machines
| Machine | Rate | Fuel |
|---|---|---|
| Burner drill | 0.25 ore/s (15/min) | 1 coal / 26.7 s (~6.7 ore per coal) |
| Stone furnace | 0.3125 plates/s | 1 coal / 44 s |
| **Drill+furnace drop-pair** | **≈0.25 plates/s sustained** (drill-limited) | ≈3.6 coal/min per pair |

A drop-pair is the S1 unit of economy. Everything below prices in pairs.

### S1 recipe costs (RCON-verified, iron plates unless noted)
| Item | Recipe | Total cost |
|---|---|---|
| Stone furnace | 5 stone | 5 stone |
| Burner drill | 3 plate + 3 gear + 1 furnace | **9 Fe + 5 stone** |
| Drop-pair (drill + drop furnace) | | **9 Fe + 10 stone + ~8 coal starter** |
| Offshore pump | 2 gear + 3 pipe | 7 Fe |
| Boiler | 4 pipe + 1 furnace | 4 Fe + 5 stone |
| **Steam engine** | 10 plate + 8 gear + 5 pipe | **31 Fe** (2.0 recipe — NOT 1.1's 27) |
| **Power pack** (pump + boiler + 2 engines + 10 pipe) | | **83 Fe + 10 stone** |
| Power pack, 1-engine minimum | | **52 Fe + 10 stone** |
| Green circuit | 1 plate + 3 cable | 1 Fe + 1.5 Cu |
| **Lab** | 10 gear + 10 GC + 4 belt | **42 Fe + 15 Cu** |
| Automation pack | 1 Cu plate + 1 gear (5 s craft) | 2 Fe + 1 Cu each; ×10 for the tech |

> ✅ **Audit RESOLVED (2026-07-21):** the "power with 24 plates produced"
> anomaly was an **item-duplication bug in FLE `extract_item`** — it
> inserted the *requested* stack into the player while removing only what
> the entity actually held, so every keep_fed sweep (quantity=50) minted
> plates. Found red-handed (48 ore in → 100 plates swept), patched in the
> live venv + snapshot, verified dead by `probe_dupe_audit.py` (request 50
> → receive exactly the 6 real plates). `craft_item` is **conservative**
> (verified: 31 plates → exactly 31 plates of parts) but its recursion
> re-queues intermediates on retry — budget ~20% slack above the recipe
> floors or an exact budget strands itself in parts. Full writeup:
> `patches/extract-item-duplication.md`.
> **All pre-fix production numbers (every era, both route-search nights)
> are dupe-inflated** — treat §4's tables as strategy-ranking only until
> regenerated from post-fix data.

### Rocks (the WR's opening trick — verified present on seed 424242)
| Rock | Yield | Mine time |
|---|---|---|
| **Huge rock** | **24–50 stone AND 24–50 coal** | 3 s |
| Big rock | 20 stone | 2 s |
| Big sandy rock | 19–25 stone | 2 s |

One huge rock ≈ 37 stone + 37 coal for **3 seconds** — the same haul is
**~150 s** of throttled hand-mining. Rocks are a ~50× discount and they are
100% match-legal. **Seed 424242 has a huge-rock at (8,−80) — adjacent to
the iron patch — and big-rocks at (−38,16) and (−19,24).** No skill mines
rocks yet; this is the single highest-value missing skill in S1.

---

## 2. The payoff matrices

### 2.1 Marginal value of the Nth drop-pair (the 6-vs-7-vs-8-vs-9 question)

Model: pairs placed serially (~20 s of character time each — craft 4 s +
walk/place/fuel), first pair down at 0:50 after a rock-funded bootstrap;
effective pair output 0.22 plates/s (fuel-gap discount on 0.25); ~25 s
ore→plate→swept pipeline latency. Plates delivered **by 5:00**:

| Pairs (iron) | Cumulative plates by 4:00 | by 5:00 | Marginal plates of the last 2 pairs | Drill capital cost (Fe) |
|---|---|---|---|---|
| 2 | 46 | 86 | — | 18 |
| 4 | 88 | 154 | +68 | 36 |
| 6 | 117 | 205 | +51 | 54 |
| 8 | 132 | 238 | +33 | 72 |
| 10 | 137 | 253 | +15 | 90 |

Read it like a speedrunner:
- **Pairs 1–6 are almost free money** (each returns 3–8× its 9-plate cost
  within the window).
- **Pairs 7–8 still pay ~1.8–3.7×** if placed before ~3:10.
- **Pairs 9–10 barely repay by 5:00** — but a pair ALWAYS repays past the
  window (it mines forever). The 5-minute rubric undervalues late drills;
  the game does not. **Window incentives ≠ game incentives** — in match
  play (no 5:00 cliff), keep placing pairs as long as plates exist.
- Placement-time rules of thumb:
  **last iron pair that helps a 5:00 score: ~3:50. Last pair that beats
  hand-mining the same seconds: ~4:30** (a pair breaks even with hand-mining
  after only ~30 s of runtime: 15 s invested × 0.5/s hand = 7.5 ore =
  0.25/s × 30 s).

### 2.2 What a plate bank affords, and when

| Target | Cost | Affordable when… |
|---|---|---|
| 2 more pairs | 18 Fe + 20 stone | almost always — default spend |
| 1-engine power | 52 Fe + 10 stone | ~4 pairs running since ≤2:00, or 6 since ≤2:45 |
| Full 2-engine power | 83 Fe + 10 stone | ~6 pairs running since ≤2:00 |
| Lab | 42 Fe + **15 Cu** | needs a copper leg: 2 Cu pairs ≥ 30 s, or 30 ore hand (60 s) |
| Automation (10 packs) | 20 Fe + 10 Cu + lab powered | packs handcraft in 50 s — start crafting while lab is placed |

Power sequencing rule: **power before the lab, lab before more engines.**
One engine (900 kW) runs a lab (60 kW) thirty times over — the second
engine is for the *electric-drill* era (S2), not S1. If plates are tight,
1-engine power at ~3:45 beats 2-engine power at ~4:40.

### 2.3 Coal budget (the silent killer)

Each pair burns ~3.6 coal/min; the boiler ~1.35/min once lit. 8 iron pairs
+ 2 coal pairs + boiler ≈ **38 coal/min**. A coal drop-pair yields 15
coal/min mined — so **1 coal pair sustains ~4 other pairs** (its furnace is
a collector, not a smelter). Doctrine: **place 1 coal pair per 4 iron/copper
pairs, BEFORE the fleet starves** — a starved pair is capital earning 0%.

### 2.4 Walk-cost table (seed 424242, from spawn; s = d÷9, round trip ×2)

| Destination | Distance | One-way walk |
|---|---|---|
| Water (power site) | 37 | 4 s |
| Iron patch | 79 | 9 s |
| **Huge rock (stone+coal!)** | 80 (at 8,−80, by iron) | 9 s — same trip as iron |
| Stone patch | 88 | 10 s |
| Copper patch | 90 | 10 s |
| Coal patch | 108 | 12 s |

Errand doctrine: **batch by geography, not by resource.** On this seed the
huge rock and iron patch are one trip; water is trivially close (the power
trek is only ~8 s round — power is cheap in *time*, expensive only in
*plates*).

---

## 3. The route shape this math implies (match physics, unproven — the
route search's job to verify and tune)

| Clock | Action | Why |
|---|---|---|
| 0:00–0:25 | Walk to iron (9 s), **mine the huge rock** (3 s → ~37 stone + 37 coal) | funds ALL furnaces + starter fuel for ~4 s of mining |
| 0:25–1:15 | Hand-mine ~26 iron (52 s); craft 4 furnaces meanwhile | bootstrap ore; craft during mining — the queue is never idle |
| 1:15–1:45 | Place 2 bootstrap furnaces + first 2 iron pairs | economy online by 1:45 |
| 1:45–2:45 | Scale to 6 iron pairs + 1 coal pair; keep_fed sweeps | §2.1: pairs 3–6 are the best money in S1 |
| 2:45–3:45 | Bank to 52+ Fe → power_craft → power_build (1 engine first) | §2.2 affordability; water is 4 s away |
| 3:45–5:00 | 2 copper pairs → 10 GC → lab → Automation; +2 iron pairs if plates allow | closes every rubric gate; copper leg is only ~60 s |

WR yardstick: power 4:31 with ~35–40 drills (humans place faster than our
20 s/pair — closing that gap is body engineering, not strategy).

---

## 4. What our own runs say (empirical — regenerate with bible_stats.py)

Through 2026-07-20 (~225 graded S1 lanes):

**Cheat-era data** (pre-throttle, hand-mining ~50× — ranks strategies, not
routes): score rises monotonically with drill count — drills 0 → median 0,
4 → 24, 6 → 28, 8 → 31.7. Power built = +12.5 median score. Early first
drill (≤2:30) = +4.8 median. Every slice agrees with §2: **drills first,
power on top of a drill economy, earlier everything.**

**Match-physics data** (post-throttle route search): the optimizer found a
**degenerate 0-drill power-rush** (median 18.2 beats 2-drill lanes' 13.3)
— it skips the economy entirely and touches the power trophy at ~4:10.
This is a **rubric exploit, not good play**: 15 pts for power vs 1.5/drill
mispricing drills-as-capital inside a 5-minute cliff. Two fixes proposed:
weight drills ≥3 (or score plates uncapped), and/or gate power points on a
minimum economy (e.g. power counts only with ≥4 drills placed). Until the
rubric is fixed, treat search champions with 0 drills as artifacts.

**Variance note:** same-config S1 scores span ~2×. No single run proves
anything; medians of N≥8 do.

---

## 5. Map-reading: what the brain should check before committing (any seed)

1. **Rocks in a 100-tile radius** — a huge rock rewrites the opening
   (skip the stone patch entirely; coal patch can wait past 2:00).
2. **Water distance** — power trek cost = 2×d÷9 s. d<50: power is nearly
   free in time, gate it on plates alone. d>150: consider deferring power
   toward the end of the window (or 1-engine minimum).
3. **Iron–coal adjacency** — pairs need 3.6 coal/min each; if coal is >60
   tiles from iron, budget a coal pair EARLY (the resupply walk eats the
   keep_fed cycle).
4. **Patch shape** — a wide face fits more pairs without crowding (our
   measured crowding failure: repeated mine_lines on one face run out of
   spots). Rows of 4 with 7-tile pitch.
5. **Trees near the build zone** — wood is pole fuel and (later) poles;
   ~1 s each to chop in passing, never a dedicated trip in S1.

## 6. Open items this bible surfaces

- **sk_rocks** — mine rocks near the route (the #1 missing skill; legal,
  ~50× discount, present on our own seed).
- **Rubric v2** — fix the 0-drill power-rush exploit (§4).
- **Craft accounting audit** — the 24-plate power anomaly (§1) must be
  resolved before match-mode claims.
- **Craft-while-walking probe** — vanilla crafts during walks; if FLE
  blocks, we're legally *slower* than human hands and should patch FLE.
- Auto-inject this bible's §1–§3 tables into brain workdirs (BIBLE_CARD
  carries the distilled version; keep them in sync).
