# EVALUATION.md — our system vs the field (2026-07-19)

An honest audit of the current arena stack against everything in
[RESEARCH.md](RESEARCH.md)/[LEARNINGS.md](LEARNINGS.md), grounded in live run
data (the factory_one run in progress today, read through `decisions.py`).
Answers three questions: the biggest bottleneck, what makes us best in the
world, and what infinite Fable credits would buy.

---

## 0. Where we stand

Our stack is already ahead of most of the field: persistent `claude -p` brains
with account rotation, a distilled speedrun playbook, PLAN/LESSONS file memory,
pinned map seed, scorecard, and a per-decision ledger. That is more scaffold
than anything on the FLE leaderboard ever had (the leaderboard entries used the
paper's deliberately minimal scaffold, and no external result has ever been
posted).

What we're missing is almost the entire **"calculators for the LLM" layer**
that every independently-successful project converged on:

| Field-validated technique | Us today |
|---|---|
| Automated-score feedback (the leaderboard metric) | ❌ raw PS only — our best run farmed hand-crafting the metric ignores |
| Ratio oracle (FactorioCalc) | ❌ model derives ratios in-head |
| Deterministic spatial helpers (outpost tiler, belt A*, diagnose) | ❌ model does geometry in-head |
| Structured placement diagnostics (why + blocker + actual_position) | ❌ opaque errors |
| Debug-loop breaker (live intervention) | ❌ ledger detects loops only post-hoc |
| Topology audits (whole-chain, on a clock) | ❌ per-entity status peeks |
| TAS/WR pacing oracle | ❌ generic "zoom out" nudge |
| Blueprint paste (`_load_blueprint` + library) | ❌ unused |
| Game-state commit/restore/undo | ❌ repair-forward only |
| HUD fixed-context (diary + namespace display) | ➖ partial: claude -p holds history server-side, uncontrolled compaction |
| Backtracking repair sub-agent | ❌ main agent burns steps on fixes |
| Playbook + file memory + retros | ✅ have it, works |
| Pinned map + scorecard + decision ledger | ✅ have it — nobody else measures at all |

---

## 1. Biggest bottleneck: the agent is a surveyor, not a builder

Live evidence from today's run (19 steps, ~9.5 minutes at time of audit):

- **Steps 10–17: eight consecutive steps fighting drill placement** — probing
  the ore boundary, `can_place` returning True while `place_entity` refuses,
  footprint misalignment. Each step bought Δscore ≈ 30–75.
- Nine minutes in: **6 entities, zero phase gates hit.** The playbook target is
  ~11 drills by minute 10.
- Cadence ≈ 29s/step (median think 15s + pacing + eval), and each step is one
  timid program — an effective build rate of a couple of entities/minute during
  exactly the phase a speedrunner blitzes.

This is the FLE paper's core finding reproduced in our own ledger: the model
spends its decision budget doing **geometry and state-probing in its head** —
work that should be one deterministic function call. (Paper numbers: frontier
failures are 97.7% pragmatic/wrong-state, 0% syntax; spatial F1 0.24 vs human
0.76.)

Secondary bottlenecks, in order:

2. **Wrong score signal.** We feed and optimize raw production score, which
   counts hand-crafting; the leaderboard differentiator is **automated score**
   (`score()` returns both). Our best prior run's "craft 100 packs/cycle score
   engine" was farming points that don't count.
3. **No live debug-loop breaker.** ClientBusy (step 5) and the placement fight
   (steps 13–14) each burned multiple steps re-deriving what LESSONS.md
   already knew. The field's #1 documented waste (78×-repeated calls).
4. **Decision throughput.** One small program per ~29s when the env happily
   executes a 40-line program that places an entire outpost.

## 2. What we add to be best in the world

Ranked by expected Δscore-per-effort (this is ROADMAP Phases 3–5, prioritized):

1. **Pre-seeded helper library in the agent's Python namespace** —
   `plan_outpost(patch)` (tile drills + collection belt), `route_belt(a,b)`
   (ported A*), `audit_chain(line)` (whole-topology check), `why_blocked(pos)`
   (structured diagnostics), `ratio(item, rate)` (vendored FactorioCalc).
   Converts the eight wasted survey steps into one call each. Every successful
   project converged here; **nobody has built it on top of FLE** — that's the
   open crown.
2. **Automated-score feedback + playbook rewrite.** One-line arena change;
   permanently kills the hand-crafting attractor.
3. **Debug-loop breaker + WR pacing oracle in the watchdog.** The ledger
   already detects loops post-hoc — make it intervene live; replace the
   generic zoom-out with "WR pace: logistics by 14:56 — you're at 22:00 with
   no assemblers. That's the fire."
4. **Blueprint paste** (`_load_blueprint` + curated early-game library, decoded
   via draftsman). The one potential step-change no leaderboard entry used;
   it's inside the env and legal.
5. **Game-state checkpointing + cheap repair sub-agent.** "Commit, try,
   restore-on-failure" replaces repair-forward; a ≤20-line-program `claude -p`
   fixer keeps the main context clean.

Our unique structural edge: **the harness itself.** Subscription-parallel
Claude sessions, a pinned map, and an A/B runner design. Nobody else in this
field runs controlled experiments at all — we can measure each change above in
a day and compound only what wins.

## 3. Infinite Fable credits: out-performing a human

The human's 20/24-vs-7/24 advantage is grounded execution, not knowledge. With
unlimited compute you don't out-think the human — you **out-sample** them.
FLE's save/load makes the world *forkable*, which turns Factorio into a search
problem a human physically cannot play:

- **Tree search over world states (the core move).** Run N parallel FLE
  instances. At each decision point, fork the save; 4–8 Fable sessions each
  execute a different candidate strategy in their own fork for K steps at game
  speed 10; score the forks (automated-score slope + WR pacing); the winner's
  world becomes canon; repeat. MCTS where the rollout policy is Fable and the
  simulator is the actual game. A human gets one timeline; this gets thousands.
- **Best-of-N at the program level.** Sample 5 candidate programs per step;
  pre-validate offline (draftsman collision check, FactorioCalc ratio check,
  `can_place`/`get_connection_amount` dry runs); execute only the survivor.
  Most errors die before touching the world.
- **A specialist org that actually works** (unlike CCPF's untested
  bureaucracy): a slow, high-effort *planner* owning the goal stack and pacing;
  parallel *builders* executing macros in claimed zones; a *cartographer*
  maintaining a queryable world DB (FactoryVerse pattern); an always-on
  *auditor* running topology checks and pushing warnings into sessions;
  *repair* agents draining an error queue. Our arena already runs N agents in
  one world — this is personas + zoning away.
- **Self-improvement across runs.** Nightly league on the pinned map;
  auto-retro mines each ledger into ERROR TIPS; verified programs get banked
  into a retrieval skill library (Voyager loop). The playbook improves
  measurably every night; the human's skill is static.
- **Offline knowledge factories.** Thousands of lab-play rollouts purely to
  harvest failure taxonomies and blueprint-verified layouts before official
  attempts.

Endgame: fork-based search + per-step best-of-N + a compounding skill library
should push lab-play past the human's 20/24 (each task becomes "search until
solved") and scale open-play score with parallel compute, where the human is
capped at one pair of hands. Honest caveat: open-play wall-clock matters (the
world runs while you think), so search must live in high-speed forks with cheap
commits — which FLE's tick-aware `sleep` and speed-10 settings already support.

## Verdict

The fastest path is unchanged: **ROADMAP Phase 3 first** — the helper library
and automated-score switch are prerequisites for everything above, and they are
days of work, not weeks. Then A/B every addition on the pinned map and let the
ledger decide.
