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

## Open items

- Legal-mode skill layer: belt/inserter logistics skills (hand-hauling is
  now the worst option); measure the legal-mode score penalty (predicted 3–5×).
- Placement crowding: repeated mine_lines on one patch run out of spots
  (Fable: 17 calls → 36 entities). Needs patch-aware row layout.
- Periodic score=0 / entities=None RCON blips pollute ledgers — filter or fix.
- League automation (Phase 5 of EVAL-PLAN.md): scheduled matches,
  LEADERBOARD.md, auto-retro into the playbook.
- Multi-agent teams: zoning works via persona + `home`; role specialization
  (miner/logistics/power) untested. 3v3 team-vs-team is the target format.
