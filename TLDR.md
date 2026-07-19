# TLDR — factorio-agents

**What this is:** a multi-agent Factorio arena. FLE (factorio-learning-environment)
runs headless Factorio; Claude brains (`claude -p` subscription sessions with
account rotation) write Python programs against the FLE API each step; a HUD,
watchdog, scorecard, and per-step decision ledger watch the runs.
**Goal: play Factorio better than anyone else in the world.**

**Why that's achievable:** the FLE leaderboard still holds only the authors'
original March-2025 entries — **no external scaffold has ever posted a result**.
Best model ever: 21.9% lab-task success; a human novice scores 83% through the
same API. The documented failure modes (78×-repeated failing calls, never
auditing factory topology, wrong beliefs about game state) are all fixable with
scaffolding — which is exactly what we build.

**The one strategic correction:** production score counts hand-crafting; the
leaderboard's real metric is **automated score**, which excludes it. Our agents
must automate, not hand-craft for points. (`score()` returns both.)

**The consensus architecture** (every successful project converged on it):
deterministic calculators/macros on the game side + one aggregated factory
snapshot per turn + a thin LLM choosing among verified operations. Never make
the model do pathfinding or ratio math. Text observations beat vision.

## The files

| File | What it holds |
|---|---|
| [RESEARCH.md](RESEARCH.md) | Full survey: 36 repos code-read, FLE paper + peer reviews, expertise-as-code (FactorioCalc, TAS routes, belt routers), ranked technique list |
| [EVALUATION.md](EVALUATION.md) | Us vs the field: gap table, the bottleneck (with live run evidence), best-in-world additions, infinite-compute design |
| [LEARNINGS.md](LEARNINGS.md) | Distilled rules: what the field learned + what our own runs taught us |
| [ROADMAP.md](ROADMAP.md) | The master plan — eval phases + scaffold upgrades, sequenced, with status |
| [EVAL-PLAN.md](EVAL-PLAN.md) | The measurement plan (scorecard → ledger → A/B → VS mode → league) |
| `arena.py` | The runner: N agents, one world, claude-p brains, personas |
| `scorecard.py` / `decisions.py` | Run snapshots + per-decision Δscore ledger |
| `arena-logs/<agent>-workdir/` | Each agent's CLAUDE.md playbook, PLAN.md, LESSONS.md |

## Where we are / what's next

- ✅ Arena runs end-to-end; pinned map seed; scorecard + decision ledger (eval
  phases 1–2 done).
- 🔜 Next (ROADMAP Tier S): switch feedback to automated score, vendor
  FactorioCalc as the ratio oracle, TAS build-order + WR pacing file,
  debug-loop breaker, topology audits.
- 🔜 Then: HUD fixed-context scaffold (replace sliding window), repair
  sub-agent, game-state commit/undo, spatial helper library, A/B experiments.
