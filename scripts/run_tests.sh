#!/bin/bash
set -e
TARGET=${1:-all}

case "$TARGET" in
  unit)
    echo "=== Frontend unit tests ==="
    cd frontend && npm run test:unit && cd ..
    echo "=== Backend unit tests ==="
    cd backend && python -m pytest tests/ -k "not integration" && cd ..
    ;;
  integration|e2e|perf)
    echo "TODO: implement $TARGET"
    ;;
  all)
    "$0" unit && "$0" integration && "$0" e2e
    ;;
  full)
    "$0" all && "$0" perf
    ;;
  *)
    echo "Usage: $0 [unit|integration|e2e|perf|all|full]"
    exit 1
    ;;
esac
