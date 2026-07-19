#!/bin/sh
# sequential match queue — waits for any running experiment, then runs the rest
cd "$(dirname "$0")"
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
while pgrep -f experiment.py >/dev/null; do sleep 60; done
echo "=== MATCH 2: sonnet vs haiku ==="
uv run python experiment.py --vs configs/vs-sonnet-haiku.json --minutes 45 --label match2-sonnet-vs-haiku > match2.log 2>&1
echo "=== MATCH 3: sonnet vs sonnet+foreman ==="
uv run python experiment.py --vs configs/vs-sonnet-advised.json --minutes 45 --label match3-advisor > match3.log 2>&1
echo "=== QUEUE DONE ==="
uv run python scorecard.py report
