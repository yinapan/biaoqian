#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
mkdir -p tests/performance/reports
SUMMARY=tests/performance/reports/baseline_day1_$(date +%Y%m%d).txt
echo "=== Day 1 k6 baseline (20 runs) $(date) ===" > "$SUMMARY"
echo "run | search_p95 | suggestions_p95 | filter_p95 | failed" >> "$SUMMARY"
SEARCH_TOTAL=0
SUGG_TOTAL=0
FILT_TOTAL=0
N=20
for i in $(seq 1 $N); do
  OUT=$(MSYS_NO_PATHCONV=1 docker run --rm --network host -v "$(pwd):/work" -w /work grafana/k6:latest run tests/performance/k6-baseline.js --quiet 2>&1)
  SEARCH=$(echo "$OUT" | grep "scenario:search_baseline" | grep "p(95)" | sed -E 's/.*p\(95\)=([0-9.]+)ms.*/\1/' | head -1)
  SUGG=$(echo "$OUT" | grep "scenario:suggestions_baseline" | grep "p(95)" | sed -E 's/.*p\(95\)=([0-9.]+)ms.*/\1/' | head -1)
  FILT=$(echo "$OUT" | grep "scenario:filter_definitions_baseline" | grep "p(95)" | sed -E 's/.*p\(95\)=([0-9.]+)ms.*/\1/' | head -1)
  FAIL=$(echo "$OUT" | grep "http_req_failed" | sed -E 's/.*: ([0-9.]+)% .*/\1/' | head -1)
  echo "$i | $SEARCH | $SUGG | $FILT | $FAIL%" >> "$SUMMARY"
  echo "Run $i: search=$SEARCH ms, sugg=$SUGG ms, filt=$FILT ms, failed=$FAIL%"
  SEARCH_TOTAL=$(python -c "print($SEARCH_TOTAL + float('$SEARCH'))")
  SUGG_TOTAL=$(python -c "print($SUGG_TOTAL + float('$SUGG'))")
  FILT_TOTAL=$(python -c "print($FILT_TOTAL + float('$FILT'))")
done
SEARCH_MEAN=$(python -c "print(round($SEARCH_TOTAL / $N, 2))")
SUGG_MEAN=$(python -c "print(round($SUGG_TOTAL / $N, 2))")
FILT_MEAN=$(python -c "print(round($FILT_TOTAL / $N, 2))")
echo "" >> "$SUMMARY"
echo "MEAN | $SEARCH_MEAN | $SUGG_MEAN | $FILT_MEAN | 0%" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "Day 1 mean P95 (over $N runs):" >> "$SUMMARY"
echo "  search_baseline: $SEARCH_MEAN ms" >> "$SUMMARY"
echo "  suggestions_baseline: $SUGG_MEAN ms" >> "$SUMMARY"
echo "  filter_definitions_baseline: $FILT_MEAN ms" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "Day 2 fill: THRESHOLD = 1.2 × mean (round up)" >> "$SUMMARY"
echo "  THRESHOLD=$(python -c "import math; print(math.ceil(max($SEARCH_MEAN, $SUGG_MEAN, $FILT_MEAN) * 1.2))")" >> "$SUMMARY"
cat "$SUMMARY"
