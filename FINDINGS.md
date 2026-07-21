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
