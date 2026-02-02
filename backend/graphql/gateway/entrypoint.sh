#!/bin/bash
set -e

echo "Apollo Router Entrypoint - Composing Supergraph..."

# Wait for subgraph services to be ready
wait_for_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    echo "Waiting for $name at $url..."
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo "✓ $name is ready"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "✗ $name failed to respond"
    return 1
}

# Wait for all subgraph services
wait_for_service "user-service" "http://graphql-user-service:8000/health"
wait_for_service "robot-service" "http://graphql-robot-service:8001/health"
wait_for_service "site-service" "http://graphql-site-service:8002/health"

echo ""
echo "All services ready. Composing supergraph schema..."

# Compose supergraph using rover (accept ELv2 license)
export APOLLO_ELV2_LICENSE=accept
rover supergraph compose --config /etc/router/supergraph-config.yaml --elv2-license accept > /tmp/supergraph.graphql

if [ $? -eq 0 ] && [ -s /tmp/supergraph.graphql ]; then
    echo "✓ Supergraph composed successfully"
    echo ""
    echo "Starting Apollo Router..."
    exec /dist/router --config /etc/router/router-config.yaml --supergraph /tmp/supergraph.graphql --dev
else
    echo "✗ Failed to compose supergraph"
    exit 1
fi
