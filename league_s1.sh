#!/bin/sh
# S1 wide league: N consecutive rounds of 10 CONCURRENT lanes
# (4 baseline + 3 pace + 3 powerpack), within-round paired.
# 10 lanes = Docker-VM RAM ceiling (7.65G cap, ~530MB/server).
# Verdicts accumulate in stage-runs.jsonl; summarize with league_report.py.
cd "$(dirname "$0")"
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PYTHONUNBUFFERED=1
N=${1:-24}
i=1
while [ "$i" -le "$N" ]; do
  label="s1-wave2-$(date +%m%d)-r$i"
  echo "=== LEAGUE ROUND $i/$N ($label)"
  uv run python stage.py \
    --lane configs/stage1-x00-base.json \
    --lane configs/stage1-x01-base.json \
    --lane configs/stage1-x02-base.json \
    --lane configs/stage1-x03-base.json \
    --lane configs/stage1-x04-cad10.json \
    --lane configs/stage1-x05-cad10.json \
    --lane configs/stage1-x06-cad10.json \
    --lane configs/stage1-x07-cad45.json \
    --lane configs/stage1-x08-cad45.json \
    --lane configs/stage1-x09-cad45.json \
    --minutes 5 --label "$label" 2>&1 | grep -vE "^(Gym|Please|Users|See)"
  i=$((i + 1))
done
echo "=== LEAGUE COMPLETE ==="
