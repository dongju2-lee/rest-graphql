"""Docker stats Prometheus exporter via Docker socket API."""
import json
import time
import threading
import http.client
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

DOCKER_SOCKET = "/var/run/docker.sock"
SCRAPE_INTERVAL = 3
metrics_cache = ""

# Gateway service name → case label
GATEWAY_CASE_MAP = {
    "rest-gateway": "case1-rest",
    "strawberry-gateway": "case2-strawberry",
    "apollo-router": "case3-apollo",
}

# Infrastructure services (excluded from case tagging)
INFRA_SERVICES = {"postgres", "prometheus", "grafana", "docker-exporter"}

# Network name used by all project containers
NETWORK_NAME = "fleet-net"


class DockerSocket:
    """HTTP client over Unix socket."""
    def get(self, path):
        conn = http.client.HTTPConnection("localhost")
        conn.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.sock.connect(DOCKER_SOCKET)
        conn.request("GET", path)
        resp = conn.getresponse()
        data = resp.read().decode()
        conn.close()
        return json.loads(data)


def detect_case(containers):
    """Detect which case is running based on gateway container."""
    for c in containers:
        service = c.get("Labels", {}).get("com.docker.compose.service", "")
        if service in GATEWAY_CASE_MAP:
            return GATEWAY_CASE_MAP[service]
    return "unknown"


def calc_cpu_percent(stats):
    """Calculate CPU usage percent from Docker stats."""
    cpu = stats.get("cpu_stats", {})
    precpu = stats.get("precpu_stats", {})
    cpu_delta = cpu.get("cpu_usage", {}).get("total_usage", 0) - precpu.get("cpu_usage", {}).get("total_usage", 0)
    sys_delta = cpu.get("system_cpu_usage", 0) - precpu.get("system_cpu_usage", 0)
    num_cpus = cpu.get("online_cpus", 1)
    if sys_delta > 0 and cpu_delta > 0:
        return (cpu_delta / sys_delta) * num_cpus * 100.0
    return 0.0


def collect_metrics():
    """Collect metrics from all running containers."""
    docker = DockerSocket()
    try:
        containers = docker.get("/containers/json")
    except Exception as e:
        return f"# ERROR: {e}\n"

    # Detect which case is currently running
    current_case = detect_case(containers)

    lines = []
    lines.append("# HELP docker_container_cpu_percent CPU usage percent")
    lines.append("# TYPE docker_container_cpu_percent gauge")
    lines.append("# HELP docker_container_memory_usage_bytes Memory usage in bytes")
    lines.append("# TYPE docker_container_memory_usage_bytes gauge")
    lines.append("# HELP docker_container_memory_limit_bytes Memory limit in bytes")
    lines.append("# TYPE docker_container_memory_limit_bytes gauge")
    lines.append("# HELP docker_container_network_rx_bytes_total Network bytes received")
    lines.append("# TYPE docker_container_network_rx_bytes_total counter")
    lines.append("# HELP docker_container_network_tx_bytes_total Network bytes transmitted")
    lines.append("# TYPE docker_container_network_tx_bytes_total counter")

    for c in containers:
        name = c["Names"][0].lstrip("/")
        container_labels = c.get("Labels", {})
        service = container_labels.get("com.docker.compose.service", name)

        # Only export metrics for containers on our project network
        container_networks = c.get("NetworkSettings", {}).get("Networks", {})
        if NETWORK_NAME not in container_networks:
            continue

        # Tag with case label: infra containers get "infra", others get the detected case
        case = "infra" if service in INFRA_SERVICES else current_case

        try:
            stats = docker.get(f"/containers/{c['Id']}/stats?stream=false")
        except Exception:
            continue

        labels = f'name="{name}",service="{service}",case="{case}"'

        # CPU
        cpu_pct = calc_cpu_percent(stats)
        lines.append(f'docker_container_cpu_percent{{{labels}}} {cpu_pct:.4f}')

        # Memory
        mem = stats.get("memory_stats", {})
        mem_usage = mem.get("usage", 0)
        mem_limit = mem.get("limit", 0)
        lines.append(f'docker_container_memory_usage_bytes{{{labels}}} {mem_usage}')
        lines.append(f'docker_container_memory_limit_bytes{{{labels}}} {mem_limit}')

        # Network
        networks = stats.get("networks", {})
        rx_total = sum(n.get("rx_bytes", 0) for n in networks.values())
        tx_total = sum(n.get("tx_bytes", 0) for n in networks.values())
        lines.append(f'docker_container_network_rx_bytes_total{{{labels}}} {rx_total}')
        lines.append(f'docker_container_network_tx_bytes_total{{{labels}}} {tx_total}')

    return "\n".join(lines) + "\n"


def scrape_loop():
    """Background thread that periodically collects metrics."""
    global metrics_cache
    while True:
        try:
            metrics_cache = collect_metrics()
        except Exception as e:
            metrics_cache = f"# ERROR: {e}\n"
        time.sleep(SCRAPE_INTERVAL)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            # Use cache if fresh, otherwise collect live
            data = metrics_cache if metrics_cache else collect_metrics()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(data.encode())
        elif self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress access logs


if __name__ == "__main__":
    print("Docker stats exporter listening on :9417/metrics", flush=True)
    # Start background scraper
    t = threading.Thread(target=scrape_loop, daemon=True)
    t.start()
    server = HTTPServer(("0.0.0.0", 9417), MetricsHandler)
    server.serve_forever()
