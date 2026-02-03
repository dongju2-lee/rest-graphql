# k6 Dockerfile for Load Testing
FROM grafana/k6:latest

# Copy test scripts
COPY k6-graphql.js /scripts/k6-graphql.js
COPY k6-rest.js /scripts/k6-rest.js

WORKDIR /scripts

# Default command (can be overridden)
CMD ["run", "k6-graphql.js"]
