# factorio-agents

A multi-agent **Factorio arena**: headless Factorio (via
[factorio-learning-environment](https://github.com/JackHopkins/factorio-learning-environment),
"FLE") played by **Claude brains** — persistent `claude -p` subscription
sessions that write Python programs against the FLE API every step — wrapped in
our own measurement stack: pinned map seed, run scorecard, per-decision ledger,
A/B experiment runner, live head-to-head VS mode, and a spectator dashboard.

**Goal: play Factorio better than anyone else in the world.**

That's less crazy than it sounds. The FLE leaderboard still holds only the
authors' original March-2025 entries — **no external scaffold has ever posted a
result**. The best model ever managed 21.9% lab-task success where a human
novice scores 83%, and the documented failure modes (78×-repeated failing
calls, never auditing factory topology, wrong beliefs about game state) are all
fixable with scaffolding. Scaffolding is what this repo builds. Full survey:
[RESEARCH.md](RESEARCH.md).

## How it works

```
┌─────────────────────────────────────────────────────────┐
│ Factorio headless server (Docker, FLE cluster,          │
│ pinned map seed — every run is the SAME world)          │
└──────────────▲──────────────────────────▲───────────────┘
               │ RCON                     │ RCON
        ┌──────┴───────┐          ┌───────┴────────┐
        │  arena.py    │          │ scorecard.py   │
        │  N agents,   │          │ decisions.py   │
        │  one world   │          │ dashboard.py   │
        └──────▲───────┘          └────────────────┘
               │ prompt / program / feedback
        ┌──────┴──────────────────────────┐
        │ ClaudePBrain: `claude -p` with  │
        │ --resume (persistent session),  │
        │ subscription account rotation   │
        └─────────────────────────────────┘
```

- **`arena.py`** — the runner. N agents share one world (FLE's
  `A2AFactorioInstance`), each with its own character, isolated Python
  namespace, model, and persona, running in parallel threads. Each step: the
  brain gets the latest observation, replies with reasoning + one
  ` ```python``` ` block, the arena executes it in the game, and feeds back the
  output, production score, and a fresh inventory/nearby-entities snapshot.
  Every ~8 steps a "zoom out" nudge (and optionally a **foreman advisor** — a
  one-shot stronger model reviewing recent progress) is injected.
- **Brains** are subscription-billed `claude -p` sessions (`--resume` keeps the
  conversation server-side) with automatic rotation across
  `~/.clawd-accounts/*` login pools on rate limits — or plain metered API
  (`"brain": "api"`). Nested-Claude env vars (`CLAUDECODE`, `CLAUDE_CODE_*`,
  `ANTHROPIC_API_KEY`) are scrubbed so the child bills the subscription.
- **Agent memory** lives in `arena-logs/<agent>-workdir/`: a `CLAUDE.md`
  playbook distilled from human speedruns, plus `PLAN.md` / `LESSONS.md` the
  agent maintains itself with Read/Write/Edit.
- **Configs** in `configs/*.json` override agents/goal/steps/pacing via the
  `ARENA_CONFIG` env var — the config file *is* the experiment definition.

## Quickstart

Prereqs: Docker, [uv](https://docs.astral.sh/uv/), the `claude` CLI logged in
on a subscription (accounts under `~/.clawd-accounts/`, or use the `"api"`
brain with `ANTHROPIC_API_KEY` in `.env`).

```bash
uv sync

# 1. start headless Factorio (fresh pinned world)
uv run fle cluster start -n 1 -s open_world

# 2. run the arena (config optional; defaults live at the top of arena.py)
FLE_SPECTATOR_MODE=1 ARENA_CONFIG=configs/solo-opus.json uv run python arena.py

# 3. watch
uv run python dashboard.py     # live HUD on http://<lan-ip>:8790
tail -f arena-logs/factory_one.jsonl
```

Verify map determinism any time with
`uv run python scorecard.py fingerprint` (identical hash across boots ⇔ the
seed pin is working).

## Running experiments

```bash
# A/B: two configs, fresh pinned world each, same wall-clock, verdict table
uv run python experiment.py --a configs/solo-opus.json \
    --b configs/solo-sonnet.json --minutes 45 --label opus-vs-sonnet

# VS: two agents live in ONE world (separate territory, head-to-head score)
uv run python experiment.py --vs configs/vs-sonnet-opus.json --minutes 45

# queue several matches back-to-back
./run_queue.sh
```

The measurement contract ([SCORING.md](SCORING.md)): the headline metric is
**median automated production score after 60 wall-clock minutes on the pinned
seed, over N ≥ 3 runs** — automated score (FLE's `score()[1]`) excludes
hand-crafting, which is the leaderboard's real differentiator. One variable per
experiment; the decision ledger explains *why* a change won or lost; winners
merge into the baseline config.

## Tool inventory

| File | What it does |
|---|---|
| `arena.py` | The runner: N agents, one world, claude-p brains, personas, foreman advisor |
| `experiment.py` | A/B runner (`--a/--b`) and live head-to-head (`--vs`) on the pinned map |
| `scorecard.py` | `snapshot` world state → `runs.jsonl` · `report` table · `fingerprint` determinism check · `vs` territory score |
| `decisions.py` | Per-step ledger: each program's intent, Δscore, Δentities, stall flags, phase-gate times |
| `dashboard.py` | Live spectator HUD (:8790): world state, agent transcripts, think times |
| `speed_watchdog.py` | Pins `game.speed=1` while a human client spectates (box64 server can't sustain speed 10 + lockstep client) |
| `bake_scenario.py` | Bakes FLE's Lua library into the scenario so a human Factorio client can join without the "handlers not identical" refusal |
| `run_queue.sh` | Sequential match queue |
| `configs/` | Experiment definitions (solo/VS, model matchups, advisor on/off) |

## The docs

| Doc | What it holds |
|---|---|
| [TLDR.md](TLDR.md) | One-page orientation: what/why/status |
| [RESEARCH.md](RESEARCH.md) | The field survey: 36 repos code-read, FLE paper + peer reviews, expertise-as-code, ranked technique list |
| [FLE-USAGE.md](FLE-USAGE.md) | GitHub trace of how others build on FLE: middle-brain specimens, claudetorio arena, fork analysis, the unclaimed lane |
| [LEARNINGS.md](LEARNINGS.md) | Distilled rules — what the field learned + what our own runs taught us |
| [EVALUATION.md](EVALUATION.md) | Us vs the field: gap table, the bottleneck, best-in-world plan, infinite-compute design |
| [ROADMAP.md](ROADMAP.md) | The master plan, phased and sequenced, with status |
| [EVAL-PLAN.md](EVAL-PLAN.md) | The measurement design (scorecard → ledger → A/B → VS → league) |
| [SCORING.md](SCORING.md) | The objective metric, iteration rules, and immediate next steps |

## Status

Arena, pinned seed, scorecard, decision ledger, A/B runner, and VS mode all
work end-to-end (ROADMAP Phases 0–2 ✅). Next up (Phase 3): wire **automated
score** through everything, vendor FactorioCalc as the ratio oracle, TAS
build-order + world-record pacing, debug-loop breaker, topology audits — then
A/B each change on the pinned map and let the ledger decide.

The one-line doctrine, from everything the field has learned:

> Give the model calculators, oracles, and macros; feed it one fresh
> aggregated snapshot per turn; keep its programs short and self-verifying;
> break its loops; audit topology on a clock; and score only what's automated.
