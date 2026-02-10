#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting Case 2: Strawberry GraphQL Gateway..."
docker compose -f "$PROJECT_ROOT/docker-compose.case2.yml" up -d --build

echo "Waiting for services to be healthy..."
for i in {1..30}; do
  if curl -sf http://localhost:10000/health > /dev/null 2>&1; then
    echo "✓ Strawberry Gateway is ready!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "ERROR: Gateway failed to start in time"
    exit 1
  fi
  echo "Waiting... ($i/30)"
  sleep 2
done

echo ""
echo "✓ Case 2 (Strawberry GraphQL) ready!"
echo "  Gateway:  http://localhost:10000"
echo "  GraphQL:  http://localhost:10000/graphql"
echo "  GraphiQL: http://localhost:10000/graphql"
echo ""
echo "Example query:"
echo '  curl -X POST http://localhost:10000/graphql \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"query":"{ fleetDashboard { robots { id name status } } }"}'"'"
