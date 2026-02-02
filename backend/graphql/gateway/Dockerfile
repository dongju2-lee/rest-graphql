# Apollo Router Dockerfile
FROM ghcr.io/apollographql/router:v2.10.0

# Copy router configuration and supergraph schema
COPY router-config.yaml /etc/router/router-config.yaml
COPY supergraph-config.yaml /etc/router/supergraph.yaml

# Expose ports
EXPOSE 4000 8088 9090

# Run router with supergraph schema
CMD ["--config", "/etc/router/router-config.yaml", "--supergraph", "/etc/router/supergraph.yaml", "--dev"]
