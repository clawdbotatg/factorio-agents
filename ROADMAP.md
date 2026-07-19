# ROADMAP.md — master plan to the best Factorio-playing agent in the world

Merges the measurement plan ([EVAL-PLAN.md](EVAL-PLAN.md)) with the scaffold
upgrades from the research sweep ([RESEARCH.md](RESEARCH.md) §7, rules in
[LEARNINGS.md](LEARNINGS.md)). Sequenced so every scaffold change lands with a
measurable A/B. Status: ✅ done · 🔨 in progress · ⬜ next.

## Phase 0 — Arena foundation ✅
- ✅ Multi-agent arena (`arena.py`): N agents, one world, FLE
  A2AFactorioInstance, claude-p brains with account rotation, personas,
  speedrun playbook CLAUDE.md + PLAN.md/LESSONS.md memory, HUD, watchdog.

## Phase 1+2 — Measurement ✅ (commit e879949)
- ✅ Pinned map seed (verified identical boots) — every run on the SAME map.
- ✅ `scorecard.py` snapshots → `runs.jsonl`; `decisions.py` per-step decision
  ledger (Δscore/Δentities per program, wasted-step + error-loop flags,
  phase-gate timestamps).

## Phase 3 — Score right + expert oracles ⬜ (Tier S — do next)
The cheapest points; strategy fixes before machinery.
1. ⬜ **Automated score everywhere**: feedback line, HUD, scorecard, ledger
   show `score()[1]` (automated) beside total. Playbook rule: hand-crafting is
   bootstrap-only. Retire the craft-100-packs "score engine".
2. ⬜ **FactorioCalc vendored** into agent workdirs; playbook: compute machine
   counts/ratios via `import factoriocalc` BEFORE building. factoriolab
   `data/1.1/data.json` alongside as ground truth.
3. ⬜ **BUILD_ORDER.md + WR pacing oracle**: distill the AnyPct TAS (35,456
   parseable actions: exact order, fuel counts, 46-tech research order) into a
   phase file; add WR split table (automation 6:13, logistics 14:56 …). The
   zoom-out nudge becomes "you are N min behind WR pace at <tech> — why?".
4. ⬜ **Debug-loop breaker** (watchdog): ≥2 near-identical program+error pairs
   → inject forced re-plan prompt ("stop; different approach; check
   LESSONS.md"). Attacks the 78×-repeat failure mode.
5. ⬜ **Topology audit cadence**: every ~8 steps run a whole-chain audit
   program (source→belt→inserter→machine→output per production line) instead
   of per-entity status peeks.

**Gate:** A/B on the pinned map (Phase-5 runner or manual): Phase-3 scaffold vs
current — expect automated-score, not vibes, to decide.

## Phase 4 — Context & memory scaffold ⬜ (Tier A)
6. ⬜ **HUD fixed-context**: replace the sliding 40-message window with FLE's
   3-message shape — system / accumulated reasoning diary / fresh HUD (score,
   automated score, flows, Tree-formatted state, live namespace vars). Port
   from `fle/eval/inspect/integration/solver_utils.py`.
7. ⬜ **Compounding ERROR TIPS**: LESSONS.md gets lifecycle rules (active vs
   resolved, root causes, session-start consolidation) and is spliced into the
   system prompt each session (CCPF workspace pattern).
8. ⬜ **Backtracking repair brain**: on program error, loop a cheap `claude -p`
   fixer (≤20-line programs, tiny fresh context) until fixed or N tries, then
   return to the main agent.
9. ⬜ **Game-state VCS**: expose FLE commit/restore/undo to agents; auto-commit
   per step; playbook: "checkpoint before risk".
10. ⬜ **Re-ground on resume/handoff**: account handoffs and watchdog kicks
    send "observe all state first, then continue" — never bare continue.

## Phase 5 — Spatial competence ⬜ (Tier B)
11. ⬜ **Namespace helper library** pre-seeded each run: `audit(area)`,
    `why_blocked(pos)` (WidAmi diagnose + autorio error taxonomy),
    port-geometry/drop-position oracles, verified 2.0 offsets.
12. ⬜ **Belt router + outpost tiler**: enforce `connect_entities` over manual
    belt placement; port FactorioBeltRouter A* and outpost.js miner tiling as
    helpers.
13. ⬜ **Blueprint library**: curate early-game blueprints (smelting column,
    red-science block, SAT-solved balancers), decode via draftsman, paste via
    FLE's `_load_blueprint` admin tool. Measure the score step-change.
14. ⬜ **Playbook absorbs the CCPF cookbook**: belts-terminate-at-inserters,
    stale-variable re-fetch, rotate-input-inserter, crafting-rate table,
    BuildingBox/nearest_buildable discipline.
15. ⬜ **Warning push**: watchdog injects "NO_FUEL×22" style alerts into the
    session instead of waiting for the next observation. Optional: multi-zoom
    `_render` PNGs attached to feedback (text stays primary).

## Phase 6 — Experiments & events ⬜ (EVAL-PLAN phases 3-5)
16. ⬜ `experiment.py` A/B runner (same pinned map, same wall-clock, verdict
    table). First experiments: each Phase 3-5 item on/off; Sonnet vs Opus;
    playbook vs none; pacing 8s vs 30s; solo vs duo.
17. ⬜ VS mode: two agents, separate forces, live scoreboard.
18. ⬜ League: nightly cron match, auto-scorecard, auto-retro that rewrites the
    playbook, LEADERBOARD.md pushed.

## Phase 7 — Claim the crown ⬜
19. ⬜ Run FLE's official eval settings (open_play 5000 steps, lab-play
    throughput tasks, pass@8) with the full scaffold + a minimal-scaffold
    baseline for comparability; track the paper's metrics (PS + slope,
    milestones, automation milestones, error rate + taxonomy, most complex
    item, debug-loop lengths).
20. ⬜ Submit to the FLE leaderboard — it still holds only the authors'
    March-2025 entries; any solid external result is historic.

## Standing rules
- Every scaffold change ships with an A/B on the pinned map; the decision
  ledger explains *why* a change won or lost.
- Retros append to [LEARNINGS.md](LEARNINGS.md) §B; playbook edits cite a
  learning or an experiment.
- Repo docs: [TLDR.md](TLDR.md) is the entry point — keep it current when
  phases flip to ✅.
