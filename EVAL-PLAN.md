# Arena Evaluation Plan

Goal: turn "do the agents play well?" from vibes into scored, repeatable,
comparable experiments — and then into live head-to-head events.

## Phase 1 — Scorecard + pinned map (build NOW)
- **Seed pinning**: cluster boots write a fixed-seed `map-gen-settings` file
  into the container before launch → every world is the SAME map. Verified by
  entity-fingerprint comparison across two boots.
- **`scorecard.py snapshot --label <run>`**: captures built-entity counts,
  production stats, tech state, game tick, config (roster/models/pacing) into
  `runs.jsonl`. `scorecard.py report` prints a comparison table across runs.
- Arena auto-snapshots at run start/end.

## Phase 2 — Per-decision ledger (granular eval)
- Every step already returns FLE's production score. Arena logs a `score`
  event per step: {step, production score, entity count, tick}.
- `decisions.py <run>` renders the decision ledger: for each step, the
  program's intent (first thought line), its Δscore and Δentities — "what did
  this decision buy?" Flags: wasted steps (Δ=0 runs of 3+), error loops,
  maintenance vs growth ratio, phase-gate timestamps (first drill / power /
  assembler / belt / science).
- End-of-run: score curve + top-5 best/worst decisions → feeds the retro.

## Phase 3 — A/B experiment runner
- `experiment.py --a config_a.json --b config_b.json --minutes 60`: runs A
  then B on the SAME pinned map (world reset + resource regen between),
  same wall-clock, auto-scorecards both, prints the verdict table.
- First experiments: (1) Sonnet vs Opus, same playbook. (2) Playbook vs no
  playbook. (3) Pacing 8s vs 30s. (4) Solo vs duo.

## Phase 4 — VS mode (live head-to-head in ONE world)
- Two agents, **separate Factorio forces** (red/blue): own tech, own
  entities, can't touch each other's machines. Spawns offset ±80 tiles on
  the pinned map (mirrored resources as fair as the map allows).
- Score = per-force production statistics, live on the HUD as a scoreboard
  (red vs blue plates/min, score totals, phase gates hit).
- Event framing: "Agent A (sonnet) vs Agent B (opus) — final score X:Y" /
  "A has a planning advisor, B doesn't". Same infra, different loadouts —
  the BYO-harness arena in miniature.

## Phase 5 — League automation
- Scheduled events (cron): nightly match, auto-scorecard, auto-retro that
  rewrites the playbook, `LEADERBOARD.md` in the repo, results pushed.
