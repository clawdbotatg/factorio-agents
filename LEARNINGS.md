# LEARNINGS.md — distilled rules for making Claude play Factorio well

Two sources: **the field** (36 repos code-read + FLE paper + peer reviews —
details in [RESEARCH.md](RESEARCH.md)) and **our own arena runs** (agent
LESSONS.md files + run retros). Kept short and prescriptive; this is the file
to reread before changing the scaffold or playbook.

---

## A. What the field learned (validated across projects)

### Strategy & scoring
1. **Automated score is the real metric.** Raw production score counts
   hand-crafting; the leaderboard differentiator is automation (Claude 3.5 beat
   GPT-4o 293k vs 88k with the SAME milestone count — the difference was 13 vs
   9 *automation* milestones). Hand-crafting is bootstrap-only.
2. **Research investment separates winners.** Only Claude invested in tech in
   the paper's open-play; electric drills produced a ~1.5× score jump. Greedy
   short-horizon play (300 hand-crafted wooden chests) is the default failure.
3. **Models know everything and it doesn't help.** They have wiki-level recipe/
   ratio knowledge from pretraining but a human novice still wins 20/24 vs 7/24.
   Don't spend prompt on recipes — spend it on grounding and state.
4. **Measure SPM (science/min) and score *slope*,** not "biggest factory";
   fixed step-caps right-censor score (trajectories still rising at cutoff).

### The failure modes to scaffold against (paper numbers)
5. **Debug loops are the #1 waste**: same failing call repeated 78+ times;
   56% of steps error even in successful runs. Detect repetition → force a
   strategy switch. Error recovery IS the game.
6. **Topology blindness**: models check individual entities, never the whole
   chain (source→belt→inserter→machine→out). Schedule whole-factory audits;
   per-entity status checks won't find gridlock.
7. **Failures are pragmatic, not syntactic** (Opus 4.1: 97.7% wrong-beliefs-
   about-state, 0% syntax). Scaffold state-tracking (re-fetch entities, diff
   state, namespace display), not code correctness.
8. **Spatial reasoning is the hard ceiling** (model F1 0.24 vs human 0.76).
   Every successful mitigation moved geometry OUT of the model: A* routers,
   layout synthesizers, port-geometry tables, collision pre-checks.

### Architecture (the convergent design)
9. **Deterministic skill/macro layer under the LLM.** The model picks
   skill+params; code owns positions, rotation, fueling, drop offsets. Macros
   place what they can and return `{ok, placed, missing, errors}`.
10. **One aggregated snapshot per turn** — counts by type, statuses grouped,
    patches as centroid+total. Never per-tile dumps; never make the model ask
    5 questions to learn where it is (inject position/tick every turn).
11. **Structured failure diagnostics pay for themselves.** Placement errors
    must carry *why* (collision + blocking entity, invalid terrain) and
    `actual_position`. One project measured 30% of a session lost to opaque
    "Placement blocked" errors.
12. **Text beats vision.** Nobody successful uses screenshots in the loop;
    sparse structured text beat dense ASCII *and* images (belt gaps are a
    "Where's Waldo" failure for VLMs). If vision at all: annotated renders
    with a JSON legend, or multi-zoom sprite renders — as a supplement.
13. **Short programs, assert early.** "A failed assertion at line 10 lets you
    re-sample; failure at line 90 is wasted compute" (FLE's own prompt).
    Longest-program model (133-line avg) had the most errors.
14. **Memory = files with lifecycle**, not growing chat history. FLE's best
    scaffold is a FIXED 3-message context: system + reasoning diary + fresh
    HUD (score/flows/state/live namespace vars). Error tips compound in a
    structured report; stale entity data gets scrubbed.
15. **Checkpoint before risk.** Game-state commit/restore/undo turns Factorio
    into a REPL with rollback — recovery becomes "restore" instead of "repair
    forward".
16. **Re-ground on every resume/handoff**: "observe all state first, then
    continue" — never bare "continue". Factorio state goes stale fast.
17. **Ratio math belongs to a solver.** FactorioCalc (pip) computes exact
    machine counts/inputs; the TAS route + WR split times are an expert
    build-order and pacing oracle. The model should *consult*, not derive.

### Ops footguns (from people who ran 24/7)
18. RCON: 4096-byte limit; batch 3-5 ops/call (60-300 ops/s vs 6.6 naive);
    RCON return only means the action *started* — use file/UDP streams for
    completion. Two warm-up commands to swallow the achievements banner.
19. Use a vanilla save, not a scenario (multiplayer desync); bump
    `drop-detection-threshold-time` for long model stalls; FLE `sleep()` is
    tick-aware (cheap at high game speed).

---

## B. What our own runs taught us (arena retros, keep honoring)

1. **ClientBusy is the silent killer**: a busy-client craft silently no-ops and
   the program keeps going; the NEXT placement fails confusingly. Craft in
   small batches with sleeps, big crafts in their own program, re-probe
   inventory after any crash.
2. **Drill direction = drop direction, not facing.** Check `.drop_position`
   after EVERY placement. Confirmed auto-feed geometry: furnace row y, drill
   row y-2 facing DOWN → drop lands on the furnace.
3. **Placement loops can snap two entities to one tile** — print returned
   `.position` and dedupe.
4. **Travel in ≤25-tile hops** with retries; long `move_to` wedges the
   pathfinder. Never walk a long corridor without doing 100% of the business
   at both ends.
5. **Warnings lie**: drills report "output blocked / no sink entity" while the
   furnace IS accepting — trust climbing inventory counts over warnings.
   Furnaces/chests can't sit on ore tiles; belts can.
6. **Craft >~100 units exceeds the 60s program cap but still completes** —
   only trailing prints are lost. Keep batches ~100, put the craft LAST.
7. **Run-2 fatal gap: zero assemblers, zero belts after a full hour** — 2,605
   gears hand-crafted. Phase gate: no assemblers running by ~program 20 →
   stop everything and build them. (Generalized by field learning A1:
   hand-crafting doesn't even score under automated_score.)
8. **A crashed program shows near-zero/negative score but the factory is fine**
   — score is a rate; re-probe before reacting.
9. **The playbook works when followed** — burner bootstrap → power → smelting
   columns → assemblers is the human speedrun shape; drift happens when the
   agent freelances early. Zoom-out nudges every ~8 steps catch drift late;
   the debug-loop breaker + pacing oracle (ROADMAP) should catch it early.

---

## C. The one-line doctrine

> Give the model calculators, oracles, and macros; feed it one fresh
> aggregated snapshot per turn; keep its programs short and self-verifying;
> break its loops; audit topology on a clock; and score only what's automated.
