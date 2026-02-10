#!/bin/bash
set -e

PROJECT_ROOT="/Users/idongju/dev/secret/graph-rest-preform"

echo "Starting Case 3: Apollo Router (Federation)..."
docker compose -f "$PROJECT_ROOT/docker-compose.case3.yml" up -d --build

echo "Waiting for subgraphs to be healthy..."
for i in {1..30}; do
  if curl -sf http://localhost:10011/health > /dev/null 2>&1 && \
     curl -sf http://localhost:10012/health > /dev/null 2>&1 && \
     curl -sf http://localhost:10013/health > /dev/null 2>&1; then
    echo "✓ All subgraphs are ready!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "ERROR: Subgraphs failed to start in time"
    exit 1
  fi
  echo "Waiting for subgraphs... ($i/30)"
  sleep 2
done

echo "Waiting for Apollo Router..."
for i in {1..30}; do
  if curl -sf http://localhost:10000/ -X POST -H "Content-Type: application/json" -d '{"query":"{ __typename }"}' > /dev/null 2>&1; then
    echo "✓ Apollo Router is ready!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "ERROR: Router failed to start in time"
    exit 1
  fi
  echo "Waiting for router... ($i/30)"
  sleep 2
done

echo ""
echo "✓ Case 3 (Apollo Router Federation) ready!"
echo "  Router:   http://localhost:10000"
echo "  GraphQL:  http://localhost:10000 (POST)"
echo ""
echo "Example query:"
echo '  curl -X POST http://localhost:10000 \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"query":"{ robots { id name latestTelemetry { batteryLevel } } }"}'"'"
