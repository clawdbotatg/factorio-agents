# FINDINGS — what the matches actually taught us

Experiment log for the agent-arena. Raw data: `runs.jsonl` (scorecard
snapshots), `arena-logs/*.jsonl` (per-agent decision ledgers, gitignored).
Dates: 2026-07-19. All brains are subscription-billed `claude -p`
(clawd-p-agents) — no metered API.

## The headline result

**Model tier does not predict the winner in this game; harness quality and
strategy style do.** Across seven head-to-heads, the cheapest model (Haiku)
never lost, the most expensive reasoning didn't pay, and the single biggest
score jump came from a harness change (skills mode: 5× on production).

## Match record

| # | Format | Result |
|---|--------|--------|
| 1 | Sonnet vs Opus, 60 min VS, plain mode | Sonnet **8285 : 1464** |
| 2 | Sonnet vs Haiku, 45 min VS, plain | Haiku **1278 : 1257** (Sonnet fumbled its opening 22 min) |
| 3 | Sonnet vs Sonnet+Opus-foreman, 45 min VS | plain Sonnet **5784 : 1080** — advice *hurt* (review latency ate 27% of decision steps) |
| ab1 | plain vs skills (both Sonnet), 10-min sprints | skills: **30 ents / 2510 plates** vs 16 / **0 plates** |
| ab2 | skills-Sonnet vs skills-Haiku, 10-min sprints | Haiku **85 ents / 3065 plates** vs 40 / 1128 |
| — | skills-Fable, same sprint | 36 ents / 2634 plates — smartest plans, mid-pack score |

Same-model variance is large (Sonnet: 8285 → 1257 → 5784 across matches;
30 → 40 entities across identical sprints). Any single-match verdict inside
~2× is noise. Haiku's 85 vs Sonnet's 30/40 is outside the band.

## Why skills mode wins (the architecture finding)

Plain mode: the LLM writes a Python program every step; the character stands
idle (~30–60 s) between programs, and furnaces starve while it thinks.
Plain-Sonnet produced **zero plates in 10 minutes** — 17 entities built,
none fed.

Skills mode (`skills.py`): the LLM only returns a JSON **priority queue** of
skill calls (`mine_line{iron, n:3}`); a scripted autopilot executes them
back-to-back and runs `keep_fed` (refuel, sweep plates, restock coal)
whenever idle. Planning happens in a background thread — the body never
stops. Results: ~130 actions per 10 min instead of ~10, ~6 LLM calls per
match instead of ~90, and the decision ledger becomes 6 legible strategy
calls with score deltas instead of 90 code blobs.

The design rule that emerged: **skills stay dumb-but-reliable; placement
strategy, ordering, scaling, and timing stay with the model.** Over-script
and every match ties; under-script and you're measuring typing speed.

## What the brains revealed about themselves (skills mode, same map)

- **Haiku** won by aggression + clock-awareness: mine lines scaled 2→3→5+4→7+7
  as the match progressed; final plan at minute 8: *"no new builds pay back —
  max keep_fed ×10 to extract production from the surplus."*
- **Sonnet** planned fastest (8 s thinks) but cautiously: n=3–5 forever,
  four redundant smelt_bootstraps.
- **Fable** made the deepest reads — skipped power entirely as negative-EV in
  a 10-min match (correct), identified stone as the true bottleneck, tried to
  submit an *empty* queue for the endgame ("just sweep") — and still lost to
  Haiku because placement crowding and a parser bug (empty queue rejected —
  since fixed) blunted its edge. Better game theory, worse harness fit.
- **Opus as a foreman** (advice every 6 steps) subtracted value: the worker
  lost 27% of its steps waiting on reviews.

## Infrastructure facts worth remembering

- The headless server simulates at **~500 UPS (8.3× real time)** on this box;
  that's the CPU ceiling (speed=10 doesn't help). 10 wall-min ≈ 80 game-min.
  A speed watchdog pins 1× whenever a human is connected.
- **`claude -p --model claude-fable-5` serves real Fable on all accounts**
  (verified via response modelUsage 2026-07-19). An earlier "silent Opus
  fallback" finding was stale/probe-buggy. Retest before trusting negative
  availability claims.
- 10-minute sprints on the pinned seed (424242) discriminate clearly —
  the ab1 gap was visible by minute 2. Full dev loop: ~12 min, or ~25 for
  a two-sided A/B (`experiment.py`).
- **fast mode vs legal mode** (`"fast": false` in a config): FLE's fast mode
  teleports characters and skips craft time — great for benchmark sprints,
  looks like cheating to a spectator. Legal-player mode (walking, real craft
  times) is the exhibition/product format; it makes travel a real cost, which
  should force belt logistics into the skill layer (hand-hauling stops
  scaling). First legal-mode run: trio-haiku co-op, 3 zoned agents,
  20 s plan cadence.

## Legal-mode result (trio-haiku, 3 zoned agents, 64 min, 20 s plans)

85 entities (matches the 10-min teleport sprint) but only **300 iron
plates vs 3,065 in 10 sprint minutes — a ~60× production-throughput drop**,
and power was never reached. Building survives legality (one-time walk);
*feeding* does not (recurring walk): keep_fed went from seconds to minutes
per sweep, so drills starved between rounds. Zero brain errors across
~1,100 Haiku planning calls. Conclusion: in legal mode, belt/inserter
logistics is the highest-leverage skill missing — hand-hauling stops
scaling exactly like it does for human players.

## Staged segment evals (SEGMENTS.md) — s1-batch1, 2026-07-20

First batch of concurrent 5-min legal-mode Stage-1 ("Power", WR split 4:31)
sprints: 4 solo-Haiku MB-0 lanes on 4 parallel cluster instances via
`stage.py`. Result: scores 0 / 4 / 0 / 0 of 100 — and four load-bearing
failure modes, none of them "the model is dumb":

1. **Two lanes ran brainless**: sub3/ef/austinmax pools were at their weekly
   limit; every `claude -p` returned rc=1 and the lane fell back to autopilot
   defaults forever. Fix: `stage.py` now preflights every account pool and
   aborts if a lane has no live pool.
2. **First-skill race**: `nearest()` fails with "Could not find nearby
   resource" right after world init; the opening gather died instantly and
   poisoned the whole craft chain (no stone → no furnaces → no plates → no
   drills/pump). One retry 20 s later succeeds. Fix: gather retries; skills
   self-provision missing inputs one hop deep.
3. **keep_fed idle spin**: with nothing built, the idle filler no-oped ~130×
   at 1.4 s/eval — 4 of the 5 minutes doing literally nothing. Fix: idle
   no-op → 6 s backoff + immediate replan request.
4. **Haiku thinks too long for a 20 s cadence**: 26–58 s per plan, 2–5k
   output tokens of reasoning for a 6-line JSON. Fix: `MAX_THINKING_TOKENS=0`
   in the brain env (probe: 25 tokens, 3.8 s) + BE TERSE prompt rule.

Meta-lesson, same as ever: harness failures dominate model quality. The lane
that scored 4/100 was the one whose brain worked — it recovered from the
gather race on its own ("world may be initializing — retry"), which no other
lane got the chance to do.

**s1-batch2** (hardened accounts/retries/terse-brain, still 0/6.4/0/0):
brains now all alive and re-planning sensibly every ~20–30 s — the loss moved
down a layer into the body. Two killers in the lane-C trace: (1) the
**ClientBusy cascade** — in legal mode a timed-out walk keeps running
server-side, so every following primitive call (feed the furnace, gather)
dies with "client is already busy"; furnaces sat placed-but-unfed → 0 plates.
(2) **one hung skill ate 428 s of the 300 s window** (timeouts sized for
hour-long matches). Fixes: prelude now wraps all primitives in a
wait-and-retry busy armor; per-config `timeout_cap` (150 s for stages); the
render thread (another source of concurrent client calls) is off for stage
runs (`ARENA_NO_RENDER=1`).

**Probe-driven root causes (2026-07-20, `probe_skills.py` — deterministic
no-LLM runs of the S1 skill sequence at pinned 1×):**

- **Legal-mode primitives are cheap** — walk-to-patch 1.4 s, harvest 40 ore
  0.2 s, craft 0.7 s (at FLE's default ~8× speed; multiply by ~8 at pinned
  1×). The 60× trio production collapse was never physics — it was bugs:
- **The entombment bug (the big one):** `try_place` walked to the build spot
  and placed at offsets *including the character's own tile*. FLE's
  `place_entity` happily builds ON the character; a character embedded in an
  entity can never drain its walking queue, and legal-mode `move_to`
  long-polls that queue → every later walk hangs forever, evals time out,
  the timed-out actions keep running server-side (zombies), and the client
  desyncs (empty inventory reads). Fast mode teleports, so none of this ever
  showed in sprint benchmarks. Fix: stand OFF the build spot (reach is ~10
  tiles), place from distance; `_touch()` tries insert/extract from where we
  stand and only walks *adjacent* (never onto) an entity as fallback.
- **FLE namespace persistence drops imports and top-level state** between
  evals (a module import poisons it; even a plain list NameErrors later).
  The prelude must be functions-only.
- After the fixes the loop closed for the first time in legal mode:
  gather 22 s → place 6 s → **feed 0.3 s** → keep_fed 12 s sweeping **28
  plates**; next cycle 78 plates; pump + steam engine + pipes crafted from
  scratch. Remaining: rare long-walk pathfinder wedges (mitigation: 90 s
  timeout caps so a wedge costs one quantum, not the run) and power-path
  prechecks (boiler consumes a furnace; poles need copper — dropped from the
  S1 power chain entirely).

## S1 brained baseline established (s1-batch4/5, 2026-07-20)

With the body fixed, brained lanes went from median 0 (batches 1–3) to:
batch-4 (first working batch): 5.5 / **43.4** / 20.2 / 4.0 — the 43.4 lane
built power at **1:32** (script does 2:54, WR split 4:31) then scaled to 7
drills; the losers spam-retried BLOCKED power (→ controller cooldown added)
or wedged on the water trek (→ power split into craft/build quanta).
batch-5 (post-fix, 4× baseline): **27.5 / 10.7 / 39.2 / 37.6, median ~32.5**,
all lanes mining, 2/4 power built (2:45, 3:46). Baseline variance band
≈ 11–39; the script alone scores ≈ 38 — so the bar for any middle-brain
variant is **beating ~38 consistently**, and today's brains roughly match
the script, not yet beat it. Next lever: affordability in the status (the
brains' remaining failure is queueing builds before plates exist).

batch-6 exposed the hallucination mode (brain declared "power online" while
power_craft sat BLOCKED, then chased copper — the FLE paper's
wrong-beliefs-about-state failure, live in our ledger). batch-7 added the
**truth checklist + AFFORD line** to every status: floor rose from 5.5 to
20.7 (21.7 / 26.3 / 20.7 / 42.9, no collapsed lanes, 4+ drills everywhere,
2/4 power). Checklist kept. Variant verdicts (pace / powerpack) now
accumulating via `league_s1.sh` (4 rounds × within-batch pairing).

Batch-7 also triggered a whole-system audit vs the speedrun goal:
[WR-PACE.md](WR-PACE.md) — on a pinned seed the middle-brain search has hit
its asymptote (brains ≈ the ~38 script across batches 4–7); the next gains
are route engineering (copper/lab/research legs, unpinned-speed route
search, wedge watchdog), not brain variants.

## Wide-league verdict (s1-wide, 6 rounds × 10 lanes, n=60, 2026-07-20)

First statistically real variant comparison (10 concurrent worlds per round,
`league_s1.sh` + `league_report.py`):

| variant | n | median | mean | power% |
|---|---|---|---|---|
| base | 24 | **27.0** | 26.1 | 25% |
| pace-oracle | 18 | 24.2 | 25.5 | 33% |
| powerpack plan | 18 | 24.1 | 26.2 | 33% |

**Both variants are worthless** — medians within noise of baseline. Prompt
pacing hints and a scripted bigger opening don't move Haiku; outcomes are
dominated by execution variance and build ORDERING. The timeline data showed
the real lever: lanes that build furnaces before drills flatline at 30
plates (bootstrap batch only — furnaces without drills have no ore income),
while drills-first lanes compound 30 → 122+. → **drills-first doctrine**
added to the catalog; overnight wave 2 (24 rounds × 10 lanes) tests it plus
the plan-cadence sweep (10s vs 20s vs 45s).

## S1 bible built + three discoveries from ground-truthing (2026-07-20)

[S1-BIBLE.md](S1-BIBLE.md): the first-five-minutes decision bible — RCON-
verified recipe costs, marginal drop-pair payoff matrix (pairs 1–6 return
3–8×, 9+ only pay past the window), coal budget (1 coal pair per 4 pairs),
walk-cost table, map-reading rules. `bible_stats.py` regenerates its
empirical tables from stage-runs.jsonl; the distilled BIBLE_CARD (auto-
injected into brain workdirs) now carries the numbers. Three discoveries:

1. **Rubric exploit live in the route search**: under match physics the
   optimizer converged on a 0-drill power-rush (median 18.2 beats drilled
   lanes) — 15 pts for power vs 1.5/drill misprices drills-as-capital in a
   5-min window. Needs rubric v2 (weight drills ≥3 and/or gate power points
   on ≥4 drills).
2. **Craft-accounting anomaly**: power_built logged with ~24 plates produced
   vs a ground-truthed 52-plate single-engine floor — FLE may be leaking
   craft ingredients (silent physics cheat). Parity-audit before any
   match-mode claim.
3. **Seed 424242 has a huge-rock at (8,−80)** (24–50 stone + 24–50 coal, 3 s
   mine, adjacent to iron) + two big-rocks near spawn — the WR's rock trick
   is available and no skill uses it. sk_rocks is the top missing S1 skill.

## Overnight route search under match physics (2026-07-21, 232 generations)

The WR-PACE pivot ran all night: evolutionary search over skill-plan routes,
10 script-only lanes per generation at 4× lab speed, ~2,300 route evals,
zero tokens — under **match-legal-or-stricter physics** (harvest throttled
to exact vanilla 0.5/s; walk measured at ~half vanilla speed; craft
overcharged vs vanilla; wiki-verified parity audit v1).

- Champion lineage honest fitness (running median): **6.2 → ~23.5** (3.5×)
  across the night. The optimizer discovered real route ideas on its own:
  cut the hand-gathered stone trip (bootstrap self-provision covers it),
  front-load one big iron haul, and in the peak lineage **drill-mine stone**
  — at vanilla hand-mining rates, even stone deserves drills.
- **Match-mode validation (1×, tag=match, no nudges, 4 lanes): four
  PERFECTLY identical runs** — score 11.5, 2 drills, 3 furnaces, 64 plates,
  gates matching to 0.01 min. The variance war is won: the route is now
  deterministic. But power is not reached in 5:00 under honest physics.
- **Lab-speed scores do not transfer to 1×** (23.5 → 11.5): at 4×, passive
  drill production earns 4× more per wall-second of body time. Lab numbers
  rank routes; only match numbers are real. (WR-PACE already mandated 1×
  revalidation — confirmed necessary.)

**The honest gap to the WR (4:31 power+lab+research+~37 drills) is
structural, and the next legal levers are identified:**
1. **FLE strips the vanilla starting kit** (`reset_character_inventory` in
   the open_world scenario) — freeplay gives 1 burner drill + 1 stone
   furnace + 8 iron plates. Restoring it is parity with every human run,
   not a cheat, and it collapses the expensive hand-mined bootstrap.
2. **Rocks**: 2 big-rocks sit near spawn (the WR's first move — instant bulk
   stone); our skills can't harvest simple-entities yet.
3. Crafting can't overlap walking in FLE (humans craft while running —
   we're legally slower); FLE walk is ~half vanilla speed. Fixing FLE-side
   walk speed UP to vanilla 8.9 tiles/s is parity, not cheating.

## The duplication bug (2026-07-21) — the craft anomaly solved

The S1-BIBLE §1 audit flag is resolved, and it was worse than suspected:
**FLE `extract_item` was an item duplicator.** It inserted the *requested*
stack into the player while removing only what the entity actually held
(plus a 3–5× inflated availability count defeating the clamp) — so every
keep_fed sweep (`quantity=50`) minted plates. Caught red-handed in
route-g110:L0: fed 48 ore, swept exactly 100 plates, built power from them.

- **Patched** (live venv + snapshot), **verified dead** by
  `probe_dupe_audit.py`: request 50 → receive exactly the 6 real plates.
  Writeup: `patches/extract-item-duplication.md`.
- **`craft_item` is clean**: 31 plates → exactly 31 plates of parts,
  conservation exact (vanilla begin_crafting underneath). One quirk: the
  recursion re-queues intermediates on every retry, so an exact-budget
  craft overcrafts parts and strands itself — keep ~20% slack over the
  recipe floors (power pack: bank ~100 Fe, not 83).
- **Blast radius: every production number ever recorded is inflated** —
  all eras, both route-search nights (their routes optimized dupe-farming:
  sweep early, sweep often). Night-2 search was stopped mid-run
  (partial champions archived to `route-champions-night2-dupe.jsonl`) and
  **relaunched under fixed physics** — the first-ever honest-economics
  route search. Regenerate S1-BIBLE §4 from post-fix rows only.

Meta-lesson (the strongest yet for the doctrine): the match-mode parity
audit isn't paranoia — the first deep audit found an infinite-resource
glitch that every prior result silently used.

## Open items

- Legal-mode skill layer: belt/inserter logistics skills (hand-hauling
  measured as the bottleneck — see legal-mode result above).
- Placement crowding: repeated mine_lines on one patch run out of spots
  (Fable: 17 calls → 36 entities). Needs patch-aware row layout.
- Periodic score=0 / entities=None RCON blips pollute ledgers — filter or fix.
- League automation (Phase 5 of EVAL-PLAN.md): scheduled matches,
  LEADERBOARD.md, auto-retro into the playbook.
- Multi-agent teams: zoning works via persona + `home`; role specialization
  (miner/logistics/power) untested. 3v3 team-vs-team is the target format.
