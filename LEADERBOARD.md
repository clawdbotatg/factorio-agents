# LEADERBOARD

## Human vs Bot — all-time

| Rank | Player | Record | Best score | Title |
|---|---|---|---|---|
| **1** | **austintgriffith** | **5–0** | **3,227** (111 built, 2,117 plates, title match 2026-07-21) | **Champion. Formerly "The Novice" — clause revoked after quintupling his own baseline under match pressure.** |
| 2 | Rival Bot (Haiku + skills) | 0–5 | 372 live / 1,521 solo | The Challenger. Built its first live power plant in the title match, then ate it to escape a hole of its own construction. |

## Match history

| # | Date | Format | Result | Cause of bot death |
|---|---|---|---|---|
| 1 | 07-21 | Co-op, shared force | Human 26–8 (entities) | Entombed itself in its own mine line; human had to dig it out |
| 2 | 07-21 | VS race | Human 588–0 (forfeit) | Builds defected to the human's force (FLE hardcoded forces) |
| 3 | 07-21 | VS race | forfeit | 252-vs-0 tech disparity + placements still crossing forces |
| 4 | 07-21 | VS race | Human ~590–0 (forfeit) | Phantom-body desync: computed every action from a position it wasn't at |
| 5 | 07-21 | **Title match** (verified fair) | **Human 3,227–372** | Self-cannibalized its power plant mid-race, then declared "run complete and stable" with an empty priority queue while losing 8:1 |

## Bot solo benchmarks (fair conditions: 1×, 20 wall-min, match physics)

468 / 722 / 1213 / 1521 — median ~968 vs the human's *pre-title* baseline
of 588. Then the title match revealed the flaw in benchmarking against a
static baseline: the human learns faster than the bot ships.

*The bot returns when it can win. — management*
