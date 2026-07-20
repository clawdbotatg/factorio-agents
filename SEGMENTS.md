# SEGMENTS.md — staged speedrun evals + the middle-brain search (2026-07-20)

The plan for the next iteration loop: divide the run the way speedrunners
divide it (STRATEGY.md §1), test each segment as a short, cheap, *concurrent*
Haiku eval, and use the segment evals to search for a good **middle brain**
(LLM decides every 20–30 s, scripted body never stops moving).

Companion docs: [STRATEGY.md](STRATEGY.md) (the phase model + WR splits this
is built on), [FINDINGS.md](FINDINGS.md) (why skills-mode + legal mode is the
frame), [SCORING.md](SCORING.md) (the long-run headline metric — unchanged).

---

## 1. The frame

- **Legal-player mode** (`"fast": false`) is the condition that matters — it's
  the exhibition/product format, and it's where the real bottlenecks show
  (FINDINGS: 60× production drop; hand-hauling doesn't scale). All segment
  evals run legal mode.
- **Game speed pinned to 1** during segment evals, so wall time ≈ game time ≈
  WR split time. Grading is done in **game ticks** (3600 ticks = 1 min), which
  makes runs comparable even if speed drifts.
- **Concurrency**: `fle cluster start -n N` boots N identical pinned-seed
  worlds on RCON ports 27000..27000+N-1. One 5-min Haiku lane ≈ 15 planner
  calls — 4 concurrent lanes is nothing against 7 subscription accounts.
  Batches are synchronized: reset all N worlds → launch N lanes → grade all.

## 2. The segments (speedrun decomposition → eval stages)

Anchored to Zaspar's WR splits + Nefrums' route (STRATEGY.md §1.1, §3.1).
Boundaries are **build events**. Each stage is evaluated standalone, starting
from a **baked save** of the previous stage done well (§4).

| Stage | Window (game time) | WR anchor | Deliverables (pass condition) | Nefrums target counts |
|---|---|---|---|---|
| **S1 Power** | 0:00–5:00 | Power 4:31 | Burner mining running; bootstrap smelting; **powerplant online** (pump+boiler+engines generating); lab placed, research started | 10 Fe + 6 Cu + 16 coal + 4 stone burner drills; mine starting rocks; keep craft queue full |
| **S2 Intermediates** | 5:00–15:00 | Intermediates 14:10 | Half iron smelting lane; **gears/belts/green-circuits automated** (assemblers, not hands); first electric miners | gears+belts assemblers first; GC with iron-overflow buffer; then inserters+miners automated |
| **S3 Labs** | 15:00–20:00 | Labs 17:26 | **9 red + 10 green science assemblers, ~30 labs**, mini-science killed | +5 boilers before science |
| **S4 Steel + Power 2** | 20:00–25:00 | Steel 22:09, Power2 23:58 | Steel + brick smelting columns (double-belted for in-place upgrade); 20-boiler powerplant | 15+15 miners on stone/coal for steel; 18 coal miners for power |
| **S5 Mall + Oil** | 25:00–30:00 | Blue mall 29:37 | Mall (chest-limited); refinery column; plastics | 8 refineries + 3 plastics |
| **S6 Blue science** | 30:00–35:00 | Blue Sci 34:23 | Chemical science automated | 18 red-circuit assemblers feeding |
| **S7 Bots** | 35:00–44:00 | Box 36:02, Mixed 43:36 | Robot frames buffered; **construction bots online** (the hinge of the whole run) | engines → frames chest-limited → roboport |

Realism check: S1 alone is currently beyond us in legal mode (the trio ran 64
min and never reached power). That's the point — **S1 is where the middle-brain
search happens first**, and each stage unlocks the next only when we can pass
it repeatably. 5-minute tests, high volume, one variable each.

### S1 rubric (encoded in `stage.py`)

Measured from the timeline poller (5 s samples, RCON), window = first 18,000
ticks. Score /100:

| Component | Points | Rule |
|---|---|---|
| Power online | 40 | any steam-engine generating (energy_generated_last_tick > 0). Full 40 by WR+30s (5:01); linear decay to 0 at 10:00 |
| Burner drills placed | 30 | 1.5 pts/drill up to 20 drills |
| Iron plates produced | 20 | plates/150 × 20, capped |
| Lab + research | 10 | 5 lab placed, 5 research running |

Gates always recorded raw (tick of first drill / first plate / power / lab /
research) — the rubric is just the headline; gate deltas are what we compare.
Later-stage rubrics get encoded when a prior stage passes (S2 = automation
gates: first assembler, first machine-made gear/belt/GC, first electric drill).

## 3. Concurrency + protocol

- `stage.py` (the segment runner): stop cluster → `start -n <lanes>` →
  wait RCON on every port → launch one `arena.py` per lane
  (`ARENA_RCON_PORT=27000+i`, `ARENA_CONFIG=<lane cfg>`) → per-lane timeline
  poller (pins speed 1, samples every 5 s) → kill at tick-window end →
  grade → append `stage-runs.jsonl` + print the batch verdict table.
- **One variable per batch.** Lanes within a batch are either N repeats of one
  config (variance measurement) or 1-vs-1-vs-1 variants against a baseline
  lane. N ≥ 3 before believing any delta (FINDINGS: same-model variance ~2×).
- Accounts: each lane gets its own account pair so rate-limit pools never
  couple lanes (7 pools available).

## 4. The save relay (stage N starts where N-1 ended well)

Two mechanisms, both confirmed available:

1. **Bake the best run**: `/server-save` works on the patched cluster
   (`save_test.py`); `docker cp` the save out. FLE's cluster generator
   accepts `save_file=` (`fle.cluster.run_envs.start_cluster`) and boots the
   container with `--start-server <save>` instead of the scenario. Arena
   connects with `ARENA_KEEP_WORLD=1` (no entity wipe).
2. **Scripted reference save** (better benchmark, do once per stage): physics
   mode is an FLE-client thing, not a world property — so we can *script* a
   perfect stage-N end-state in fast mode (teleporting builder, exact Nefrums
   counts), save it, and use that as the canonical stage-N+1 start. This
   decouples stages (S2 testing doesn't inherit S1's AI jank) and gives every
   S2 run an identical, WR-shaped starting world.

Doctrine: test each stage from the **reference save**; occasionally run
"relay mode" (real S1 winner save → S2) to measure compounding error.

## 5. The middle brain — requirements and search plan

What the trio run + skills-mode A/Bs taught us the middle brain must do:

1. **Never-idle body** — planning always in a background thread; idle queue →
   autopilot housekeeping (keep_fed today; belt-tending tomorrow).
2. **Fast decision uptake** — a 20–30 s decision cadence is useless if the
   body is stuck in a 300 s skill. Skills must execute in small quanta with
   plan-swap points between them.
3. **Compact diagnosed status in, small decision out** — the brain reads a
   digest (counts, starvation diagnosis, pace gap), returns a priority queue
   (or a menu pick). Never raw entity dumps, never code.
4. **Stage skill packs** — S1 needs power + mine-line + gather; S2 needs
   belt/inserter logistics (the measured 60× bottleneck) + assembler blocks.
   Skills stay dumb-but-reliable; strategy stays with the model.
5. **Pace oracle** — the status carries the WR split clock ("2:40, no boiler;
   WR power split is 4:31 — gap −1:51").

### Variants to test (each a lane vs the MB-0 baseline lane, same stage rubric)

| ID | Variant | One-line hypothesis | Cost |
|---|---|---|---|
| MB-0 | `skills.py` as-is (plan_every_s=20, solo) | baseline + variance band | none |
| MB-1 | **Quantized executor**: skills yield every ≤20 s quantum; re-plan applies at quantum boundaries | decision latency → uptake, fewer wasted skill-minutes | skills.py refactor |
| MB-2 | **Pace-oracle status**: WR countdown + gap line in the status prompt | clock pressure fixes priority ordering (Haiku already showed clock-awareness) | prompt-only |
| MB-3 | **S1 skill pack**: `sk_power_bootstrap` (walk-optimized pump→boiler→engine→pole chain), power-first default plan, `sk_lab` | the stage's deliverable becomes one reliable verb | new skills |
| MB-4 | **Opportunity menu**: autopilot diagnoses (n unfueled, n starved, no-power, patch distances) and emits ranked options with expected value; brain picks ids | McCarryster's shape: shrink the decision to a diagnosed menu | status builder + parser |
| MB-5 | **Event-driven replan**: replan on skill completion/failure + 30 s heartbeat (vs fixed clock) | react to failures in seconds, not next tick of the clock | controller tweak |
| MB-6 | **Standing orders**: brain sets a policy ("keep drills fed; iron→10 then power"), autopilot runs it, brain intervenes on exceptions only | fewer, better decisions; body 100% duty cycle | bigger refactor |
| — | Cadence sweep 10/20/45 s (orthogonal, on the winner) | find the knee of decisions-vs-quality | config-only |

### Brain-health metrics (recorded per run alongside the rubric)

- decisions/min actually **applied** (plans parsed & swapped in)
- status→plan latency (think time) distribution
- plan parse-failure %
- **body idle seconds** (gaps between skill executions — the metric MB-1 exists to kill)
- brain-error / account-handoff count

## 6. Immediate queue

1. **Batch 1 — variance baseline**: 4 lanes × MB-0 (solo Haiku, legal, S1,
   5 min). Establishes the S1 baseline score + variance band and shakes out
   the multi-instance runner.
2. **Batch 2 — MB-2 + MB-3** (prompt + S1 skill pack — the two cheapest,
   likeliest wins) vs 2 × MB-0.
3. **Batch 3 — MB-1 quantized executor** vs best-so-far.
4. **Batch 4 — MB-4 menu mode** vs best-so-far.
5. **Bake the S1 reference save** (scripted, Nefrums counts) → unlock S2
   testing; write the S2 rubric; start the belt-logistics skill pack (the
   known 60× bottleneck).
6. Winners merge into the baseline config; every batch gets one line in
   FINDINGS.md.
