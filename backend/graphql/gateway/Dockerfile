# Apollo Router Dockerfile with Rover for supergraph composition
FROM ghcr.io/apollographql/router:v2.10.0

# Install curl for health checks and rover for supergraph composition
USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Rover CLI
RUN curl -sSL https://rover.apollo.dev/nix/latest | sh
ENV PATH="/root/.rover/bin:${PATH}"

# Copy configuration files
COPY router-config.yaml /etc/router/router-config.yaml
COPY supergraph-config.yaml /etc/router/supergraph-config.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
EXPOSE 4000 8088 9090

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
