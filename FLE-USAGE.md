# FLE-USAGE.md — how the rest of the world uses FLE (GitHub trace, 2026-07-19)

Second research sweep, focused on one question: **how are people actually
building on factorio-learning-environment in 2026 — and has anyone built a
"middle brain" between the LLM and the game** (LLM sets priorities, a system
underneath executes)? Method: GitHub code search for FLE imports, fork
divergence analysis (87 forks checked), repo search sorted by recent activity,
plus a web/papers sweep. Companion to [RESEARCH.md](RESEARCH.md) (the original
36-repo survey).

---

## 1. Headline answers

1. **The leaderboard is still empty of external entries** — 16 months after
   launch it holds exactly the six author-run March-2025 submissions (SOTA:
   Claude 3.5 Sonnet, 293,206 PS, 21.9% lab success). Any solid
   current-frontier run submitted via the repo's `update-leaderboard.yml`
   workflow is a first-mover SOTA event. Caveat: FLE v0.4 (2026-03) migrated
   to Factorio 2.0 + an Inspect AI eval harness, so v0.4 numbers aren't
   strictly comparable to the v0.2-era leaderboard.
2. **Nobody has combined FLE with a middle layer.** The repos with real
   planner/executor architecture all run on raw RCON, not FLE; the repos on
   FLE all run flat observe→think→act loops. The combination — FLE substrate +
   semantic world model + priority/verb planner + deterministic executor — is
   an open lane no one occupies.
3. **One serious competitor is visible right now**: `bdambrosio` filed a
   scripted burst of engineering-grade FLE issues (#375–#381, all
   2026-07-17: pathfinding-treats-belts-as-walls, drop-position asymmetry,
   stale alerts, a "mod-packaged variant for persistent servers") — someone is
   running a persistent-server FLE agent stack today.
4. **Upstream FLE is active** (last commits June 2026): v0.3.0 (2025-10)
   headless + gym env + Claude Code integration; v0.4.0 (2026-03) Factorio
   2.0.73 migration with 13 breaking API changes; v0.4.3 (2026-04) Inspect AI
   sandbox eval. Community PRs are appearing (GameState serialization fix,
   structured connection-group summaries, env-init retry). Still-open author
   PRs hint at the roadmap: gamestate renderer (#280), real-time actions
   (#286), RAG agent (#158), skill library (#327).

## 2. The middle-brain specimens (best examples found, ranked)

### McCarryster/factorio_agent (2026-05, raw RCON — the real thing)
The only true **planner → executor → verifier** triad found anywhere:

- **Semantic world model** (`agent/observability/world_model.py`, 1,177 LOC):
  raw entities → typed roles (ORE_MINER, COAL_FEEDER…) → feeds-whom
  relationships → subsystem detection → power/item-flow tracing →
  **root-cause diagnosis + ranked repair opportunities** → text summary.
- **Closed-verb planner** (`agent/planner.py`): the LLM picks from **16
  ACTION_TYPES** (BUILD_* for missing infra; repair verbs like INSERT_FUEL,
  EXTEND_POWER_NETWORK, ROTATE_ENTITY) and emits structured
  `{goal, action, target, parameters, success_condition}`.
- **Deterministic skill runner** (`agent/skill_runner.py`): action type →
  parameterized Lua file, no LLM.
- **Verifier** (`agent/verifier.py`): re-observes the world and checks the
  planner's *own declared* `success_condition`.
- **Episodic memory**: completed/failed ActionRecords with a
  `recently_failed()` de-loop guard serialized into the prompt.
- Plus factory-block macros (multi-entity blueprints with material
  auto-provisioning) and a metrics dir (reward table, milestones,
  **skill_reuse** — the only project measuring whether skills get reused).

The key insight isn't the split itself — it's that the world model **shrinks
the planner's job** to picking from a diagnosed, ranked repair menu with a
machine-checkable success condition. Directly portable to FLE observations.

### lvshrd/factorio-agent (★15, ran for real, dormant since 2025-09)
The **self-growing skill library** pattern: a MainGameAgent holds 9 base tools
plus one meta-tool `manage_tools(create|list|execute|remove)`; `create`
delegates to a **CodingAgent** that RAGs two vector KBs (crawled wiki +
`runtime-api.json`) and emits parameterized Lua templates → syntax-checked
with `lupa` → wrapped in a generated Python function → hot-loaded via
importlib into a persistent versioned registry (`unified_tool_manager.py`).
The LLM extends its own action vocabulary at runtime instead of writing
one-off programs.

### guan-spicy-wolf/factorio-agent (2026-03, raw RCON + custom mod)
**3-tier Lua skill hierarchy** in the mod: `atomic/` (cursor, reach-checks,
build-from-cursor — deliberately *character-legal*, no god-mode
`create_entity`), `actions/` (composed flows like place = check inventory →
move → cursor → build), `examples/` (full tasks the agent reads as few-shot).
Self-programming with hot-reload into the running server; persistent
`agent_notes.md`; a searchable index over runtime-api.json as a tool.

### Others, briefly
- **KWeberA/factorioAgentCommunication**: not a player — a deterministic
  agent-driven test harness for mods. Steal its artifact protocol:
  run-manifest + events.jsonl + declarative action plans + assertion
  evaluation + run diffing per isolated workspace — a reproducible-scoring
  pattern.
- **nicksrusso/FactorioAgents**: 54-LOC FLE gym hello-world (confirms the
  `gym.make("iron_ore_throughput")` entry points).
- **ZelmanAi / morrejssc-hub**: design docs only, zero code (both converge on
  the same 3-layer perception/decision/execution philosophy independently).
- **Alva-Buddha/FactorioAgent**: aspirational FLE scaffolding, never ran.
- **factoriommo-agent**: 2017 human-event infra, not AI.

## 3. Claudetorio (bigsky77) — the production FLE arena that already existed

A live-streamed public "AI plays Factorio" service (Jan–Mar 2026, dormant
since 2026-03-24; ran at app.claudetorio.ai). Architecture worth knowing
because it's the closest thing to our arena at production scale:

- FastAPI **broker** orchestrates Docker slots; run-workers import FLE's
  `FactorioGymEnv` directly; every step lands in a Postgres **step ledger**
  (code/result/error/reward/production_score/achievements/token_usage), and
  step numbering survives restarts by re-fetching `step_count`.
- Two brain modes sharing one ledger: an autonomous loop, and an **MCP server**
  (`execute`/`render`/`undo`/`commit`/`restore`) so **Claude Code itself is
  the agent** — their quickstart claims a public slot and writes `.mcp.json`.
- **No middle layer** — flat loop. Its only middleware: (a) **game-state VCS**
  wired into every step (FLE's dulwich `FactorioMCPRepository`; agents emit
  `# VCS:TAG/UNDO/RESTORE` comment directives in their code), (b) FLE's
  `RecursiveReportFormatter` summarization memory, (c) the step ledger.
- **Replay = re-execution**: capture the map seed at run start, respawn
  Factorio with it later, re-run the recorded step code over RCON — no video
  stored. Spectating enabled by a **join-proof `open_world` scenario**
  (pre-register all Lua event handlers at scenario load so live human clients
  can join a headless FLE game — same class of fix as our `bake_scenario.py`).
- Robustness kit: double-`/sc` RCON warmup to clear the achievements banner,
  RCON double-connect monkeypatch, 5-consecutive-error circuit breaker,
  `fle-remote-mcp.patch` (env-var host/port so FLE drives a *remote* server).
- Watchability: haiku-class **narrator bot** answering viewers as the playing
  agent (last-10-steps + score trend as context), full VTuber → Twitch
  pipeline.
- Their `SKILL.md` "Critical API Corrections" (live-tested FLE gotchas:
  `Direction.UP` not `Direction.North`, `extract_item` arg order,
  `instance.set_speed(50)` during waits) is reusable prompt material.

## 4. Fork divergence (87 forks checked, 2026-07)

| Fork | Ahead | What |
|---|---|---|
| Center-for-Integrated-Cognition/f-l-e | **+56** | The Soar cognitive-architecture group (John Laird's lab). Last push 2026-07-17. **Not yet analyzed — top follow-up**: a cognitive architecture bolted to FLE is exactly the middle-brain shape. |
| maxrenke/f-l-e | +12 | unanalyzed |
| upMKuhn/f-l-e | +5 | unanalyzed |
| LepsyMikolaj3301/factorio-RL-TowerDefense | +5 | RL tower-defense variant |
| everyone else | 0 | vanity forks |

## 5. Web/papers sweep (2026)

- **Papers cite FLE but nobody publishes runs on it.** NeurIPS 2025
  camera-ready expanded lab-play to 33 tasks; findings unchanged.
- **The middle-brain pattern is validated in adjacent games**: **LEHCA**
  (Scientific Reports 2026) — LLM "Commander" emits strategic sub-goals +
  reward shaping + action masks, low-level RL agents execute; beats flat QMIX
  on 8 StarCraft scenarios. Also SwarmBrain ("Overmind" LLM macro over
  scripted micro). Nobody has publicly ported this shape to Factorio.
- **"Stop Comparing LLM Agents Without Disclosing the Harness"** (2026-05):
  harness configuration drives more performance variance than model choice —
  the citable justification for our scaffold-A/B methodology.
- **SUPCON** (industrial-automation vendor, 2025-09): custom sandbox,
  five-layer perceive→reason→dispatch→execute→feedback over MQTT; agents
  rediscovered expert layouts (1.18:1 solar ratio). Flat loop despite the
  layers.
- Ryan Madden (2026-04): custom RCON **CLI** (`observe-world`, `act-build`)
  because CLI suits Claude's bash affinity; flat loop; stalled mid-game;
  recommends encapsulating proven geometric arrangements (proto-skills).
- Epoch AI tracks FLE in its benchmarks hub — worth a periodic check for
  third-party model runs.

## 6. What this means for us (the middle-brain blueprint)

The user's hypothesis — "a system between the LLM and FLE where the LLM gives
priorities and a middle brain executes" — is exactly the unclaimed
combination. Every piece exists somewhere; nobody has assembled them **on
FLE**:

1. **World model → diagnosis → ranked opportunity menu** (McCarryster) — the
   observation side of the middle brain. The LLM should read "coal starvation
   at smelter row 2; top repairs: INSERT_FUEL(×22), EXTEND_BELT(a→b)" — not
   raw entity dumps.
2. **Closed verb set + machine-checkable success conditions + verifier**
   (McCarryster) — the decision contract. LLM picks verbs and declares what
   success looks like; deterministic code executes and checks.
3. **Persistent, hot-loadable, versioned skill registry the LLM can extend**
   (lvshrd), seeded with our Phase-3 helper library (`plan_outpost`,
   `route_belt`, `ratio`, `why_blocked`, `audit_chain`).
4. **Game-state VCS with agent-facing directives** (claudetorio/FLE) —
   checkpoint-before-risk, restore-on-failure.
5. **Step ledger + replay-by-re-execution** (claudetorio) — we already have
   the ledger (`decisions.py`); seed capture → deterministic replay is a
   cheap add.
6. **Commander/executor split validated by LEHCA**: our `claude -p` brain
   becomes the Commander (priorities, phase gates, WR pacing); the middle
   brain (deterministic Python + optionally a cheap fast model) drains the
   priority queue against FLE.

## 7. Follow-ups not yet run

- Deep-read the **CIC/Soar fork** (+56 commits) — the strongest unexamined
  middle-brain lead.
- Deep-read `matthewdannenberg/agentic-factorio-ai` (2026-07) and
  `AppSprout-dev/RLE` (7 role-specialized agents on Factorio).
- Check `bdambrosio/Cognitive_workbench` (the July issue-burst author),
  `lveillard/factorio-ai-companion`, `npiron/FactorioLab`, `ammar1510/ReLax`,
  maxrenke/upMKuhn forks.
- Periodic: Epoch AI FLE page; FLE leaderboard for first external entries.
