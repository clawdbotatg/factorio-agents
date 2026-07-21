# WR-PACE.md — critical audit: what it takes to run at speedrunner pace (2026-07-20)

A top-to-bottom critique of the current system (5-min S1 legal-mode trials,
skills-mode middle brain) against the actual goal: **bots that are genuinely
good at the game**. The WR (1:18:56; S1 power split 4:31) is the pace
*yardstick*, not the target — we're not competing on the human leaderboard,
we're using its splits as the best available measure of "good". Grounded in
batches 1–7 data, the probe timings, and the code as of `4592a6f`.

## 0. Where the data says we are (through s1-batch7)

- Script alone (DEFAULT_PLAN, no LLM): S1 power at ~2:54, score ≈ 38.
- Brained lanes: batch-5 median ~32.5, batch-6 collapse (median ~12, brains
  hallucinating state), batch-7 after the truth checklist: **21.7 / 26.3 /
  20.7 / 42.9, median ~24, 2/4 power (2:50, 3:00)**. Band restored; brains
  still ≈ script, never clearly above it.
- Same-config variance band ≈ 11–43. At N=4 we can only detect >2× effects.

## 1. The core critique: the brain is not the bottleneck — the ROUTE is

For a **pinned seed**, S1 (and really every early segment) is a deterministic
optimization problem. A speedrunner is not making novel decisions every 20 s;
they execute a **precomputed route** with trained exception recovery. Seven
batches of middle-brain search have produced brains that *approximate the
script*. That is the expected asymptote: on a fixed seed, the best possible
brain converges to the best route, so we're spending batch-days teaching Haiku
to rediscover DEFAULT_PLAN.

**Inversion:** optimize the route offline (scripted, searchable, measurable);
use the LLM only where the world diverges from the route or the seed is novel.

- **Route** = the speed. Hill-climb skill sequences with no LLM in the loop.
- **Brain** = robustness + generality + the show. Its honest value metric is
  Δ-over-script on **random seeds** and under injected disruption — not on
  424242, where the script must win by construction.
- This also serves the entertainment product: exhibitions on unseen seeds are
  exactly where brains visibly out-play scripts.

## 2. The search loop is running 8× slower than it needs to

`stage.py` pins `game.speed=1` "so wall time = WR split time" — but grading is
already **in ticks**. Physics is identical at any speed; this box does ~500 UPS.
Speed-1 is only needed when a *brain* is in the lane (think-time is wall-clock,
so at 8× a 20 s think costs 160 game-seconds) or when a spectator is watching.

- **Scripted route evals should run unpinned**: 5 game-min ≈ 40–75 wall-s.
  4 lanes → hundreds of route evals/day instead of ~16. That turns stage.py
  from a grader into an actual optimizer.
- Concretely: add a `--speed` flag (poller pins the requested speed); route
  search batches use max sustainable speed; brained/spectator batches keep 1×.
- With cheap evals, run an **evolutionary route search** overnight: mutate
  DEFAULT_PLAN (reorder, tune n, insert/remove quanta), eval N≥8 per candidate,
  keep the median-best. The cluster grinds; no tokens burned.

## 3. The route gap to WR is structural, not executional

WR S1 at 4:31 delivers: ~35–40 burner drills (iron+copper+coal+stone), power
plant, **lab placed, Automation researching**. Our best lane: 7 drills, no
copper, no lab. The current skill pack **cannot score above ~65/100**: every
S1-reachable electric consumer, the lab, and green circuits all need copper,
and copper isn't in the route. Missing legs (all script work, no research risk):

1. **Copper mine line + copper smelting** (unlocks everything below).
2. **sk_lab**: craft lab (10 GC + 10 gears + 4 belts) + place + power it —
   this also makes `power_gen` scoreable (a real consumer exists).
3. **sk_research**: start Automation via RCON-legal API (`set research` is a
   player action in FLE? probe it — humans click a button, so it's legal).
4. **Rocks + trees**: the WR mines starting rocks (big instant stone/coal near
   spawn) and chops trees. If FLE exposes rock harvesting, the wedge-prone
   far-stone-patch walk — our #1 variance source — may be deletable.
5. **Drill count**: rubric caps at 20; we place 4–7. After power, the script
   should default to drill spam (patch-aware rows — the known crowding issue).

## 4. Variance is the enemy of both speed and science — kill it at the harness

Sources, in impact order: pathfinder wedges (heavy tail, eats a 90 s quantum),
`nearest()` init race, brain nondeterminism, placement crowding.

- **Wedge watchdog**: RCON-side check — if the character's walking state is
  stalled >10 s, nudge it (2-tile teleport) and log the intervention. A stuck
  FLE pathfinder is a harness bug, not game physics; repairing it is not
  cheating (but log every nudge so runs are auditable).
- With 8× evals, variance gets **measured** (N≥8 medians) instead of guessed.
- Blocked-cooldown currently substitutes keep_fed even when the queue holds
  other runnable skills — skip to the next non-blocked item instead.

## 5. Micro-throughput: what a speedrunner does that the body doesn't

- **Craft while walking.** Vanilla hand-crafting continues during walking; if
  FLE's `craft_item` blocks the eval for the full craft time, the body stands
  still for every craft (~5.6 s per furnace batch at 1×). Probe whether craft
  can overlap movement; if not, it's an env constraint worth documenting (and
  possibly an FLE patch — we already run a patched snapshot).
- **Body idle seconds** between quanta (eval round-trips + `sleep(1)`) is a
  planned metric (SEGMENTS §5) that isn't instrumented yet. Instrument before
  any more MB batches — otherwise deltas can't be attributed.
- Prompt drift: CATALOG says "re-consulted every ~90 seconds"; stage configs
  run `plan_every_s: 20`. Make the prompt read the real cadence.

## 6. The legality doctrine (DECIDED 2026-07-20): lab mode vs match mode

Two modes, one hard line:

- **Lab mode** — testing and benchmarking. Any advantage is allowed (time
  compression, teleports, instant place, fast harvest, world forking, RCON
  interventions) **as long as bots are measured relative to other bots with
  the same advantage**. Lab numbers are for ranking variants, never for
  bragging.
- **Match mode** — game time: bots playing against each other for an
  audience, or playing with/against a human (co-op included). **100% by the
  rules, zero cheats.** All player actions through legal game mechanics at
  real time; RCON may *observe* (that's just seeing the screen) but never
  modify the world; no `_load_blueprint` (entity-spawning — humans can't
  paste without construction bots; reference-save baking is a lab activity);
  multiple characters are fine when the format says so (co-op is a legal
  game mode), each character individually rule-bound.

**Within lab mode, cheats split into two classes — only one transfers:**

1. **Physics-neutral** (unpinned `game.speed`, save/fork/reset, observation).
   The game plays out identically, just faster — conclusions transfer to
   match mode as-is. Use freely everywhere (this is §2's 8× search loop).
2. **Physics-altering** (teleport, instant place, fast harvest, free items).
   Valid for *relative* subsystem tests ("does brain A order skills better
   than B, travel removed?") — but they change the optimal strategy itself,
   so they rank brains/harnesses, NOT routes. Any route or logistics
   conclusion from a physics-altering benchmark must be re-validated under
   match physics before it counts.

**The gap: match mode does not exist yet.** Today's "legal mode"
(`fast: false`) still cheats: FLE hand-harvest is ~50× vanilla (probe: 40
ore ≈ 1.6 s at 1×; vanilla is 0.5 ore/s) — the whole current bootstrap
route leans on it, and it's why we "beat" the 4:31 power split at 1:32.
To stand up a real match mode:

- **Throttle harvest to vanilla rate** (patch the FLE snapshot, or a
  proportional wait wrapped around `harvest_resource` in the prelude).
  **DONE 2026-07-20** (`_hv`, 2 game-s/item = vanilla 0.5/s). Parity audit
  v1 (wiki-verified): walk — vanilla 8.9 tiles/s, FLE ≈ 4.7 → we walk at
  HALF a real runner's speed (conservative, legal); craft — FLE appears to
  overcharge vs vanilla times and cannot craft-while-walking (conservative);
  harvest — throttled to exact vanilla. Net: current physics is
  match-legal-or-stricter on every audited primitive.
- **Parity-audit every primitive** against the wiki: craft time (does legal
  mode charge it? and vanilla crafts *while walking* — if FLE can't, we're
  legally *slower* than a human there), walk speed, reach (10-tile placement
  is vanilla-legal), inventory ops.
- **No world-modifying RCON in match lanes** — the §4 wedge-nudge teleport
  is a lab-mode tool; match mode needs a rules-legal unstick (reroute, mine
  the blocker).
- Tag every graded run `lab` / `match` in stage-runs.jsonl so numbers from
  the two modes can never be accidentally compared.

Consequence for the route program: the current S1 route is tuned to the
harvest cheat. Under true match physics the optimum shifts toward the WR's
drills-first shape — so STRATEGY.md's speedrun material becomes *more*
load-bearing, and match-mode route search (§2, physics-neutral speedup only)
is the search that matters for the product.

### Seed policy (DECIDED 2026-07-20)

- **Lab mode: pinned seeds.** A fixed seed is what makes relative
  measurement work — keep 424242 as the regression baseline. But rotate a
  small **lab seed pool** too: skills and routes are already quietly
  overfitting to 424242's geography (`sk_gather` orders iron-first because
  *this seed's* stone patch is the far one). Anything that only wins on one
  map should die in the lab, not on match night.
- **Match mode: random seed, rolled at match start, always recorded** in the
  run log — random ≠ unreproducible; any match must be replayable and
  verifiable. Competitors never see the seed in advance.
- Random seeds are also what makes the brain earn its keep (§1): on a pinned
  seed the best brain converges to the script; on an unseen map the route
  becomes a *policy to adapt* — patch layout, water distance, rocks all
  move — and Δ-over-script on random seeds is the brain's honest metric.

### The three match formats

1. **Competition** — bots race the same unseen seed (separate identical
   worlds, or one shared world in VS mode). Same seed for all entrants:
   it's a race, not a map lottery.
2. **Co-op speedrun** — all bots on one team, one world, zoned roles
   (miner / logistics / power), racing the clock. Each character
   individually rule-bound; the superhuman part is coordination.
3. **Co-op with the human** — bots join the user's game to help. Different
   objective entirely: not "maximize score" but "take orders and be
   useful" — the MB-6 standing-orders shape (human sets goals, bots run
   them, interrupt only on exceptions), always at 1× (the speed watchdog
   already pins this when a human connects).

## 7. The sequenced path to a full WR-pace run

- **A (route engineering, now):** copper leg + lab + research + rock-mining
  skills; unpinned-speed route search; wedge watchdog. Exit: script S1 hits
  the real WR deliverable (power + drills incl. copper + lab + research by
  4:31-equivalent ticks) at ≥90/100 median, N=8.
- **B (the real frontier):** bake S1 reference save → S2 rubric → **belt +
  inserter logistics skill pack** (drill row → belt → furnace column via
  `connect_entities`). Hand-hauling is the measured 60× wall; S2 is where
  every FLE agent in history has died. Highest research risk in the plan —
  start it before polishing S1 further.
- **C (brains where they earn keep):** exception-handler on the fixed route
  (deviation → replan), random-seed exhibitions, stage-boundary strategy.
  Brain metric: Δ-over-script on random seeds.
- **D (superhuman levers):** 3-agent zoned co-op vs the co-op WR; fork-based
  tree search (EVALUATION.md §3) for mid/late-game layout decisions.

## 8. Batch-7 line (for the record)

s1-batch7 (4× stage1-base, post truth-checklist): 21.7 / 26.3 / 20.7 / 42.9,
median ~24, power built in 2/4 (2:50, 3:00). Checklist fixed the batch-6
hallucination collapse; brains remain ≈ script. Consistent with §1: on a
pinned seed the middle-brain search has hit its asymptote — further gains come
from the route, not the brain.
