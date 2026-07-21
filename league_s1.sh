#!/bin/sh
# S1 mini-league: N consecutive variant batches (2x baseline + pace +
# powerpack), within-batch paired. Verdicts accumulate in stage-runs.jsonl.
cd "$(dirname "$0")"
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PYTHONUNBUFFERED=1
N=${1:-4}
i=1
while [ "$i" -le "$N" ]; do
  label="s1-league-$(date +%m%d)-r$i"
  echo "=== LEAGUE ROUND $i/$N ($label)"
  uv run python stage.py \
    --lane configs/stage1-base-a.json --lane configs/stage1-base-b.json \
    --lane configs/stage1-pace.json --lane configs/stage1-powerpack.json \
    --minutes 5 --label "$label" 2>&1 | grep -vE "^(Gym|Please|Users|See)"
  i=$((i + 1))
done
echo "=== LEAGUE COMPLETE ==="
