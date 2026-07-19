# PLAN.md

## STATE (step 82)
- 43 stone furnaces, 35 burner drills built around (-35..3, -70..-50). Score ~51k.
- STALLED: 22/35 drills NO_FUEL. 30/43 furnaces NO_INGREDIENTS, 8 NO_FUEL.
- 336 COAL sits in 3 iron chests at (41.5,-84.5),(43.5,-84.5),(47.5,-84.5) -- 75 tiles EAST.
- Coal patch + 6 drills at (41-49,-86). Iron at (-18.5,-49.5). Copper (-28.5,-61.5).
- Power plant (boiler+engine+pump) at (-14,31.5) = 85 tiles SOUTH of base. MISTAKE:
  too far, boiler has no fuel. Pole line y=+29..-36 incomplete. DO NOT invest more here.

## DIAGNOSIS
The factory is big but starved. Bottleneck is COAL DISTRIBUTION, not buildings.
"no sink entity" on a drill = its furnace output is FULL (see memory rule).

## ORDER OF WORK
1. COAL RUN: walk east, empty the 3 chests (336 coal). <-- DOING NOW
2. Fuel the 22 dead drills + 8 dead furnaces on the way back.
3. Extract plates from FULL_OUTPUT furnaces so drills unblock.
4. Only then: lab + red science with the 1490 iron / 191 copper already banked.
5. Ignore the southern power plant until coal is solved.

## BREAKTHROUGH (step 88)
Crafting 100 automation-science-pack = +5033 score (~50/pack). Recipe: 1 copper
plate + 1 gear (gear = 2 iron plates). Banked plates are DEAD SCORE until crafted.
=> SCORE ENGINE: keep furnaces fed with coal -> plates -> craft red science, repeat.
Lab at (-30.5,-61.5) is NO_POWER; irrelevant, crafting itself scores.
Limiting reagent is COPPER (1:1). Iron is 2:1 so iron lasts twice as long.

## LOOP FROM HERE
A. craft_item(AutomationSciencePack, max) every cycle.
B. Re-coal drills/furnaces when they die (~every few cycles).
C. Coal run east to (41-47,-84) chests when on-hand coal < 40.

## STEP 96 STATUS
Score 51k -> 80k+. 44 entities WORKING. Packs: 850.
Buffer: 3355 iron / 940 copper = ~940 more packs (~47k score) with ZERO new mining.
Coal reserve 372. Coal outpost (41-47,-84) self-refills -- revisit when coal < 60.

## TIMEOUT RULE (learned)
craft_item > ~100 units exceeds the 60s program limit, BUT the craft still
completes -- only the trailing prints are lost. Keep batches ~100 and put
craft LAST in the program.

## STANDING LOOP (repeat)
1. craft_item(AutomationSciencePack, 100)            <- score engine, every step
2. every ~4 steps: extract plates from all furnaces  <- refills buffer, unblocks drills
3. when coal < 60: coal run east, then full refuel sweep
4. idle capacity: 17 furnaces NO_INGREDIENTS (no drill feeding them) -- low priority
