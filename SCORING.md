# SCORING.md — objective scoring, iteration method, and next step (2026-07-19)

The measurement contract for this project: how a run is scored, how experiments
are run at volume, and what to do next. Companion to
[EVAL-PLAN.md](EVAL-PLAN.md) (the phased design) and
[EVALUATION.md](EVALUATION.md) (the system audit). Tooling referenced here
exists in the repo: `scorecard.py`, `decisions.py`, `experiment.py`,
`configs/`.

---

## 1. The objective scoring method

### Instruments we have (all on the pinned map seed — every run is the same world)
- **`scorecard.py snapshot --label <run>`** → appends to `runs.jsonl`: game
  tick, entity counts by type, `entities_total`, per-item production totals
  (`produced`), tech tiers reached, and the run config. Start/end snapshots
  bracket each run; a run's value is the delta.
- **`decisions.py <agent>`** → the per-step ledger: each program's intent,
  Δscore, Δentities, wasted-step % (Δ=0 runs), error loops, and phase-gate
  timestamps (first drill / power / assembler / belt / science).
- **`experiment.py` verdict table** → compares sides on entities + key item
  counts (iron, gears, circuits, red science, top tier).

### The gap
Raw item counts aren't equal value, and none of the above distinguishes
automated output from hand-crafted output. FLE's leaderboard metric —
**automated production score** (complexity-weighted, hand-crafting excluded) —
is available in-env: `score()` returns `(total, automated)`. Until it's wired
through, experiments risk selecting for hand-crafting (which doesn't count).

### The headline metric (the number every change must beat)

> **Median automated production score after 60 wall-clock minutes on the
> pinned seed, over N ≥ 3 runs.**

Secondary metrics (recorded per run, all already derivable from the ledger +
snapshots once automated score is wired):
1. **Score slope at cutoff** — still climbing or plateaued? (fixed clocks
   right-censor; the slope is the honest tiebreak)
2. **Phase-gate times vs the WR split table** (automation 6:13, logistics
   14:56, …) — pacing, not just endpoint
3. **Science packs/min** at end of run
4. **Per-step error rate + debug-loop length distribution** (from the ledger)
5. **Milestones / automation milestones / most complex item** (leaderboard
   comparability)

## 2. How we iterate and run many performances

The loop (machinery already built):

```bash
uv run python experiment.py \
  --a configs/solo-opus.json --b configs/<variant>.json \
  --minutes 45 --label <experiment-name>
```

Each side gets a **fresh pinned world**, runs the arena under `ARENA_CONFIG`
for the same wall-clock, auto-snapshots start/end, and prints the verdict
table + per-agent decision summaries. `--vs configs/vs-sonnet-opus.json` runs
two agents live in ONE world (separate forces, territory scoring) instead.

**Rules of iteration:**
- **One variable per experiment** (model, playbook on/off, pacing, one new
  scaffold flag). The config JSON is the experiment definition; name it after
  the variable.
- **Verdict = headline metric first**, ledger second (the ledger explains *why*
  a change won or lost — wasted steps, loop lengths, gate times).
- **Repeats for variance**: the FLE paper used 8 runs; our pragmatic floor is
  3. A single run is an anecdote.
- **Winners compound**: adopted changes merge into the baseline config;
  the result (win or loss) gets one line in [LEARNINGS.md](LEARNINGS.md) §B.
- **Volume**: each side costs 45–60 real minutes, so "many performances" =
  overnight batches; the league phase (ROADMAP #18) turns this into a nightly
  cron (match → auto-scorecard → auto-retro → LEADERBOARD.md). For true
  parallelism, stand up a second FLE cluster (a second Docker instance on a
  different RCON port) and run experiments concurrently.

## 3. The next step (in order, small)

1. **Wire `automated_score` through everything** (~30 min of work):
   - `arena.py`: per-step `score` event logs both values from `score()`
   - `scorecard.py`: snapshot records `score_total` + `score_automated`
   - `experiment.py`: verdict table leads with automated score
   - Agent feedback line shows both ("score 12,400 / automated 3,100") so the
     agent optimizes the right number.
2. **Establish the baseline**: 3 × 60-min runs of the current stack
   (`configs/solo-opus.json`, pinned seed) → median automated score +
   variance. This is the bar every future change must clear; without it no
   experiment means anything.
3. **First real experiment**: build the Phase 3 helper library (vendored
   FactorioCalc `ratio()`, `why_blocked()`, `plan_outpost()`) and A/B it
   against the baseline — per [EVALUATION.md](EVALUATION.md), the change most
   likely to produce the first big jump.

**Status:** none of the three started as of this writing. #1 blocks #2 blocks
#3 — do them in order.
