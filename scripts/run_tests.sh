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
  integration)
    echo "=== Starting fixture environment ==="
    docker compose -f docker-compose.test.yml up -d --build
    trap 'docker compose -f docker-compose.test.yml down' EXIT
    echo "=== Waiting for backend health ==="
    READY=0
    for i in $(seq 1 30); do
      if curl -sf http://localhost:18000/api/v1/health > /dev/null 2>&1; then
        READY=1
        break
      fi
      sleep 2
    done
    if [ "$READY" -ne 1 ]; then
      echo "Backend not ready after 60 seconds"
      exit 1
    fi
    (cd backend && RUN_ID=local python -m pytest tests/integration/ -v --cov=app --cov-report=term)
    ;;
  e2e)
    echo "=== Building frontend ==="
    (cd frontend && npm run build)
    echo "=== Starting fixture environment ==="
    docker compose -f docker-compose.test.yml up -d --build
    trap 'docker compose -f docker-compose.test.yml down' EXIT
    echo "=== Waiting for nginx health (port 18081) ==="
    READY=0
    for i in $(seq 1 30); do
      if curl -sf http://localhost:18081 > /dev/null 2>&1; then
        READY=1
        break
      fi
      sleep 2
    done
    if [ "$READY" -ne 1 ]; then
      echo "Nginx not ready after 60 seconds"
      exit 1
    fi
    echo "=== Waiting for backend health ==="
    READY=0
    for i in $(seq 1 30); do
      if curl -sf http://localhost:18000/api/v1/health > /dev/null 2>&1; then
        READY=1
        break
      fi
      sleep 2
    done
    if [ "$READY" -ne 1 ]; then
      echo "Backend not ready after 60 seconds"
      exit 1
    fi
    echo "=== Installing Playwright chromium ==="
    (cd tests/e2e && npx playwright install --with-deps chromium)
    echo "=== Running E2E tests ==="
    (cd tests/e2e && npx playwright test)
    E2E_EXIT=$?
    exit $E2E_EXIT
    ;;
  perf)
    echo "=== Performance baseline ==="
    k6 run tests/performance/k6-baseline.js
    echo "=== Performance load ==="
    k6 run tests/performance/k6-load.js
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
