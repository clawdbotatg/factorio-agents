# RESEARCH.md — Everything known about AI playing Factorio (2026-07-19)

Deep-research sweep: ~40 public projects found, 36 cloned and code-read, plus the
FLE NeurIPS paper, its full OpenReview peer-review record, the official
leaderboard, HN threads, and every blog writeup we could find. Goal: make our
FLE + `claude -p` stack play Factorio better than anyone in the world.

Clones for direct code-lifting live in the session scratchpad under
`others/` (agent repos), `expertise/` (calculators/TAS/planners), `fle/`
(factorio-learning-environment), `ccpf/` (claude-code-plays-factorio).

---

## 1. The headline: the crown is unclaimed

- The **official FLE leaderboard still holds only the authors' original March
  2025 entries** (best: Claude 3.5-Sonnet, production score 293,206, 30
  milestones, 13 automation milestones, 21.9% lab-task success). **No external
  scaffold has ever posted a result.** o3 ties Claude 3.5 at 7/24 lab tasks —
  reasoning models did not break the wall.
- Human novice baseline (one author, <30h Factorio, same Python API): **20/24
  lab tasks vs best model 7/24**. The gap is execution, not knowledge — models
  *know* ratios/recipes better than the human (pretraining wikis) and it
  doesn't help. Don't spend prompt space on recipes; spend it on grounding.
- **Jack Hopkins didn't quit** — FLE was published at NeurIPS 2025, he was
  hired by Anthropic, and his GitHub pivoted to safety research (sandbagging,
  lie detection). `claude-code-plays-factorio` was never a living project: it's
  a one-day (2025-10-03) extraction of the FLE team's `.claude/` setup,
  published as a starter-repo demo for FLE v0.3's MCP server. FLE itself was
  active through June 2026 (v0.4.3, Factorio 2.0).

## 2. Why every agent plateaus (paper + reviews, with numbers)

- **Errors dominate:** 56% of steps in *successful* lab runs error; 30–76%
  per-step error rates in open play. Error recovery IS the game.
- **Degenerate debug loops:** agents repeated the same failing call **78+
  times**. Frontier follow-up (v0.3.0): Claude Opus 4.1's failures were
  **97.7% pragmatic** (wrong beliefs about game state), **zero syntactic** —
  scaffold for state-tracking, not code correctness.
- **Topology blindness:** when a factory underperforms, models check individual
  entities but never audit whole-structure topology (verified 3-0 by our
  fact-check pass). Nobody coordinates ~10+ machines; electronic circuits are
  the universal wall.
- **Spatial reasoning:** model F1 0.24 vs human 0.764 on spatial probes.
  Placement overlap / no room for belts / misrotated inserters dominate.
- **Greedy short horizons:** Gemini hand-crafted 300 wooden chests; only Claude
  invested in research (electric drills → ~1.5× score jump near step 3k).
- **Eval-validity caveats** (OpenReview): single map seed (generalization
  unverified), 5,000-step cap right-censors score (trajectories still rising at
  cutoff — report the slope, not just the final number), paper scaffold was
  deliberately minimal, and open-play variance/PS-gameability were never
  addressed by anyone. **PS counts hand-crafting; only `automated_score` /
  automation-milestones don't.**

⚠ **Direct hit on our current strategy:** our PLAN.md "score engine" (hand-craft
100 automation-science-pack per cycle) maximizes the *gameable* metric. The
leaderboard-differentiating metric is **automated score** — `score()` returns it
as the second element. Automate or it doesn't count.

## 3. The consensus architecture (what independently-successful projects converged on)

The three projects with real sustained progress (JJtmc1234/claude-agentic-player
— blue science + advanced oil over multi-week co-op; brickfrog/factorio-buddy —
active daily; sbarisic/FactorioMCP — real session logs) all converged, without
knowing each other, on the same shape:

> **Rich deterministic helpers on the game side + one aggregated whole-factory
> snapshot per turn + a thin LLM that chooses among verified operations.**

And the field's most quotable lesson (factorioctl README): *"Don't make your LLM
do pathfinding… Finding the right layer to make these 'calculators' for the LLM
is where all the leverage is."* Every mitigation that worked moved geometry
**out** of the model.

Meta-finding: **nobody uses computer vision in a live loop** — even the
highest-starred "CV+LLM" project (airi-factorio, 95★) ships pure RCON. Sparse
structured text beat both dense ASCII maps and screenshots (HN + FLE evidence).
When vision is used at all: annotated renders (bounding boxes + numbered JSON
legend + inserter arrows) or multi-zoom sprite renders — never raw screenshots.

## 4. Project catalog (what exists, one line each)

**The environment lineage**
- `JackHopkins/factorio-learning-environment` (1k★) — our env; paper, gym,
  MCP server, headless sprite renderer, leaderboard. Active to 2026-06.
- `JackHopkins/claude-code-plays-factorio` — 1,353-line CLAUDE.md playbook +
  4 subagents + hooks; config-only starter (see §5).
- `ProFrenchToast/FILE` — FLE wrapped as an Inspect-AI sandbox (eval pattern).
- `bigsky77/claudetorio` — 20+ parallel 24/7 headless FLE runs + Twitch
  narrator; in-code `# VCS:` checkpoint directives; RCON warm-up + desync fixes.
- `rsong9527/factorio-board` — LLM leaderboard, raw-Lua actions, `claude -p`
  backend; named-pipe (mkfifo) real-time event stream out of the mod sandbox.

**MCP / RCON bridges that actually play**
- `brickfrog/factorio-buddy` (Rust+Lua, factorioctl's successor) — ~95 tagged
  tools, plan/execute pairs returning an *executable contract*, 30s autonomy
  heartbeat, zone memory, self-filed bug reports.
- `MarkMcCaskey/factorioctl` — ASCII map w/ belt arrows, A* belt router,
  belt-network debuggers (sushi/gap/source-trace), `.agent_memory.json` zones.
- `sbarisic/FactorioMCP` (C#) — no-cheat realism; `extract_api.py` compiles the
  official runtime-api JSON into one gotcha-annotated Lua doc; annotated-
  screenshot VisionService; layout synthesis; `buildings.json`/`goals.json`.
- `JJtmc1234/claude-agentic-player` — intent LLM → JSON DSL → deterministic
  build macros (`{ok, placed, missing, errors}`); remember/recall skill memory;
  the only documented multi-week progression.
- `WidAmi/FactoMCP` — single-file server that works: `walk_to` with stuck
  detection, `diagnose_area` (no_fuel/output_full/input_empty/not_on_network).
- `lveillard/factorio-ai-companion`, `danielriddell21/factorio-mcp` (Claude
  Code plugin + skills strategy pack), `phiresky/factorio-mcp`
  (`get_player_surroundings` one-call reader), `jerome3o/factorio-mcp` (the
  Dec-2024 original), `alloc33/factorio-sensei` (read-only coach),
  `ryanmadden/autorio` (+ RUN_REPORT.md failure analysis) and `faketorio`
  (port-geometry model), `lvshrd/factorio-agent` (runtime-minted Lua tools),
  `guan-spicy-wolf/factorio-agent` (hot-reloaded dynamic scripts),
  `thedemon117/ai-player-v3` (mod-side parameterized skills),
  `linningmii` (human-in-loop safety), `nerdpudding/factorio_llm` (state
  injection), `McCarryster/factorio_agent` (M1-M18 milestone curriculum),
  `FactorioDojo/Foyager` (2023 Voyager port), `moeru-ai/airi-factorio`,
  `hrshtt/FactoryVerse` (DuckDB "database-as-vision", UDP action lifecycle),
  `matthewdannenberg/agentic-factorio-ai` (staleness-aware world model).
- Dead/stub: QVERS2309, ZelmanAi (one good idea: `request_player_help` tool),
  dested ("this doesnt work lol" — offline blueprint editing with no live
  feedback gives the agent nothing to reason about), gastrodon, kyle-compute.

**Expertise-as-code (not interfaces — game knowledge as libraries)**
- **FactorioCalc** (pip `factoriocalc`) — pure-Python factory planner w/ exact
  simplex solver + bundled v1.1 data. Verified locally: asks→"10× AM1 + 4
  copper furnaces + 1 gear AM + 7 iron furnaces + input rates" for 1 red
  science/s. **The ratio oracle our agent should import.**
- **factoriolab `data/1.1/data.json`** — cleanest machine-readable recipe/
  machine dataset; Kirk McDonald's calculator = reference solver.
- **gotyoke/Factorio-AnyPct-TAS** — WR route as **35,456 ordered actions**
  (build/put/take/walk/recipe/craft/tech…), trivially parseable; exact build
  order, fuel counts, 46-step research order. + `MortenTobiasNielsen`'s
  `goals.lua` WR split table (automation 6:13, logistics 14:56 … rocket
  1:18:56) = pacing self-eval oracle.
- **factorio-draftsman** (pip) — collision boxes, footprints, blueprint
  encode/decode, `validate_insert` overlap checks = offline placement
  validator.
- **Seancheey/FactorioBeltRouter** — cleanest belt/pipe A* (underground jumps,
  ~450 lines Lua, portable). `demipixel/factorio-generators` outpost.js — ore
  patch → tiled miners + collection belts. `Windfisch/factorio-bot`
  mine_planning.cpp — second reference. `arturh85/factorio-bot` — task DAG
  with time costs + resource-flow validation ("research automation in 8:57").
- **R-O-C-K-E-T/Factorio-SAT** + `tzwaan/factorio_balancers` — provably-correct
  balancers, precompute offline as templates. Blueprint corpora
  (brians-blueprints, Raynquist balancer book) decodable via draftsman.
- **YAFC-CE** ProductionTable.cs — LP with slack variables that *names the
  limiting link* = the bottleneck-analysis blueprint to port.
- **Voyager** (Minecraft) — curriculum agent + skill library + critic; the
  strategic-layer pattern several Factorio projects half-ported.

**Writeups / social**
- dhariri.com 2025 — commentary on FLE, no repo. jeromeswannack.com 2024 — the
  original MCP experiment. ryanmadden.net — autorio + the best failure
  postmortem. chetaslua X thread — "Claude Fable 5 plays Factorio" viral demo,
  no tooling disclosed. HN 43331582/43926829/45466865 — sparse text > ASCII >
  screenshots; agents repeat failed actions 100+×; measure SPM (science per
  minute), not "biggest factory".

## 5. Secrets from the FLE author's own stack (things our arena.py doesn't use)

1. **HUD fixed-context scaffold** — their answer to 5,000-step runs is NOT a
   sliding message window (what we do) but a **fixed 3-message context**:
   system prompt / accumulated "reasoning diary" (~8k, from prior thinking) /
   a HUD user message with score, flows, last code+output, Tree-formatted game
   state, and the **live Python variable namespace**.
   (`fle/eval/inspect/integration/solver_variants.py`, `solver_utils.py`)
2. **Recursive report memory** — every 16 messages an LLM rewrites a structured
   report (EXISTING STRUCTURES / ERROR TIPS / NAMESPACE) spliced into the
   system prompt; stale entity blobs scrubbed from old messages; error tips
   compound forever. (`fle/agents/formatters/recursive_report_formatter.py`)
3. **Game-state VCS** — `commit/restore/undo/view_history/view_code` as agent
   tools; auto-commit per step; "checkpoint before risk." Solvers also reset to
   last-good state on env error. (`fle/env/protocols/_mcp/version_control.py`)
4. **Hidden admin tools callable from agent code** (underscore names in the
   same namespace): `_load_blueprint(bp_str, position)` (paste whole
   factories!), `_save_blueprint`, `_get_production_stats`, `_render`,
   `_set_inventory`, `_regenerate_resources`. (`fle/env/lua_manager.py:265`)
5. **The "sampling opportunity" prompt** (open-play system prompt): "Each
   policy execution is a sampling opportunity… Observe → Branch → Act; fail
   fast at gates (a failed assert at line 10 lets you re-sample; failure at
   line 90 is wasted compute); n nested branches cover 2^n world-states;
   recovery is information too." (`prompts/unbounded_system.jinja2.md`)
6. **Backtracking repair sub-agent** — separate 20-line-max fixer model loops
   on errors; main context stays clean. (`examples/agents/backtracking_*.py`)
7. **Tool cookbook + crafting-rate table in-prompt**; `get_connection_amount`
   dry-runs; `nearest_buildable(BuildingBox)` discipline; tick-aware `sleep`
   (at speed 10, sleep(15) costs 1.5 wall-s). (`fle/env/tools/agent.md`)
8. **Proactive warning push** — overlay polls flows/warnings and *injects*
   "boilers out of coal" into the Claude session. (`fle/overlay_mcp.py`)
9. **Multi-zoom vision** (`FLE_VISION=true`, fat_hud 16/32/64-radius renders)
   with viewport metadata mapping pixels→coordinates.
10. **CCPF playbook gems**: mandatory read-all-manuals init; one-thing
    snippets; "assume things fail by default"; workspace memory tree
    (`notes/{successes,failures,insights}`, `bugs/{active,resolved}`,
    `references/ratios`) with session-start consolidation; resume prompt =
    "Observe your environment by accessing all available resources and then
    continue" (force re-grounding); FLE's `tests/functional/` as a library of
    guaranteed-working example code. Skip: its 4-subagent bureaucracy (never
    hardened).

## 6. Cross-ecosystem technique list (from the 36-repo sweep)

1. Deterministic skill/macro layer under the LLM; macros return
   `{ok, placed, missing, errors}`.
2. Structured failure diagnostics: placement errors carry *why* + blocking
   entity + `actual_position`; `diagnose_area` flags
   no_fuel/no_power/output_full/input_empty; decode `entity_status` to names.
3. One aggregated whole-factory snapshot per turn (counts by type, statuses,
   patches as centroid+total — never per-tile dumps).
4. Offload all spatial computation (A* belt routing w/ turn penalties +
   underground jumps, pole-coverage solvers, layout synthesizers).
5. Port-geometry tables in the prompt ("input/output tile per direction") +
   drop-position oracles; verified 2.0 offsets (drill drop = center + (0,1.297)).
6. Persistent spatial memory outside the game: zones by purpose, protected ore
   patches, auto-tracked building registry, goal journals.
7. Sandbox-escape streaming (FIFO pipe / native UDP / file-JSONL tail) —
   RCON return only means the action *started*; blocks the runtime.
8. Compile `runtime-api.json` → compact gotcha-annotated API doc.
9. Prompt discipline: inspect before mutating ("local absence is not global
   absence"); one dependent mutation per step; anti-spam-building ("every
   placement needs a purpose you can name"); hard priority gate LAST (recency);
   auto-inject `[GAME STATE: x,y,tick]` per turn.
10. Self-extending skill libraries (runtime-minted validated tools,
    remember/recall, Voyager retrieval).
11. Vision only as annotated renders or direction-glyph ASCII; text wins.
12. Ops kit: RCON 4096-byte batching (3-5 ops/call → 60-300 ops/s), warm-up
    commands, vanilla-save-not-scenario (desync), long
    `drop-detection-threshold-time` for model stalls.

## 7. THE PLAN — ranked changes to our stack

**Tier S — strategy & score (do first, cheapest per point)**
1. **Optimize `automated_score`, not raw PS.** Read both from `score()`; put
   the automated number in the HUD/feedback; playbook rule: hand-crafting is
   bootstrap-only, automation is the score engine. (Directly obsoletes our
   craft-100-packs loop.)
2. **Vendor FactorioCalc** into the agent workdir; playbook: compute
   machine counts/ratios via `import factoriocalc` before building. Add
   factoriolab data.json as ground truth.
3. **Distill the AnyPct TAS route + WR split table** into a machine-readable
   `BUILD_ORDER.md` + pacing oracle ("game-time at tech X vs WR"); phase-gate
   nudges become "you're N minutes behind WR pace at logistics — why?".
4. **Debug-loop breaker** (watchdog): detect ≥2 near-identical program+error
   pairs → inject a forced strategy-switch/re-plan prompt. Biggest documented
   waste sink (78× repeats).
5. **Topology audit cadence**: every ~8 steps, run a whole-chain audit program
   (source → belt → inserter → machine → output for each production line),
   not per-entity status checks.

**Tier A — scaffold & memory**
6. **Replace the sliding window with HUD context**: system + reasoning diary +
   fresh HUD (score/automated score/flows/state/namespace vars). Port from
   FLE's solver_utils; fits our claude -p resume model perfectly.
7. **ERROR TIPS compounding memory**: LESSONS.md gains lifecycle rules
   (bugs/active vs resolved, root causes, session-start consolidation) and is
   spliced into the system prompt, CCPF-style.
8. **Backtracking repair brain**: on program error, loop a cheap `claude -p`
   fixer (≤20-line programs, own tiny context) before returning to the main
   agent.
9. **Game-state VCS**: expose FLE's commit/restore/undo to agents; auto-commit
   per step; "checkpoint before risk" in the playbook.
10. **Re-ground on every resume/handoff**: replace bare continue with "observe
    all state first, then act" (our account-handoff fresh sessions especially).

**Tier B — spatial competence & interface**
11. **Structured failure + diagnose_area helpers**: pre-seed the namespace with
    Python helpers (`audit(area)`, `why_blocked(pos)`) that decode statuses and
    placement failures. Port WidAmi's diagnose + autorio's error taxonomy.
12. **Belt-router + outpost-tiler as namespace functions**: port
    FactorioBeltRouter A* (+ FLE's own connect_entities already does much —
    enforce its use over manual placement) and outpost.js miner tiling.
13. **Blueprint library via `_load_blueprint`**: curate early-game blueprints
    (smelting column, red-science block, balancers from Factorio-SAT), decode
    with draftsman, paste via the hidden admin tool. Potential step-change;
    verify it doesn't violate our own rules (it's within FLE's env).
14. **Port-geometry + cookbook into CLAUDE.md**: CCPF's belts-terminate-at-
    inserters, stale-variable re-fetch, rotate-input-inserter, drop offsets,
    crafting-rate table.
15. **Warning push into sessions**: our HUD/watchdog already polls; add
    "NO_FUEL×22" push injections instead of waiting for next observation.
16. **Sprite-render observation**: attach `_render` multi-zoom PNGs to the
    step feedback for spatial debugging (we already render for spectators;
    feed the agent too — but text stays primary).

**Tier C — measurement (be leaderboard-comparable)**
17. Track per-run: PS + automated PS over steps (and slope at cutoff),
    milestones, automation milestones, per-step error rate, error taxonomy
    (syntactic/semantic/pragmatic), debug-loop length distribution, most
    complex item, SPM. Multiple runs (variance is real, paper used 8).
18. Keep a minimal-scaffold baseline mode for literature-comparable numbers;
    our full scaffold is the headline, the delta is the story.
