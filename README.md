# System Information Exporter

A host-level system metrics exporter built with FastAPI and the Prometheus Python client. Exposes CPU, memory, disk, network, process, and GPU metrics via HTTP — scrape-ready for Prometheus, visualized in Grafana, with alerting through Alertmanager and an `IsolationForest`-based anomaly detector baked in.

Designed to run on a single device or across multiple machines over a Tailscale VPN — each device runs its own agent; Prometheus aggregates by scraping multiple targets under the same job.

---

## Stack

| Layer | Tool |
|---|---|
| Exporter API | FastAPI + Prometheus Python Client |
| Metric collection | psutil (CPU/memory/disk/network/processes), GPUtil (NVIDIA GPU) |
| Anomaly detection | scikit-learn `IsolationForest` |
| Monitoring | Prometheus + Alertmanager |
| Visualization | Grafana |
| Networking | Tailscale VPN (cross-device), localhost (single-device) |
| Containerization | Docker + Docker Compose |

---

## Metrics

**System**
- CPU usage (percent, per-core)
- Memory: used, available, percent
- Disk: used, free, percent — resolves root per-OS (`C:\` on Windows, `/` on Linux/macOS)
- Network: bytes sent/received, packets, errors
- Processes: PID, CPU%, memory%, RSS, thread count, status

**GPU** (NVIDIA only, degrades gracefully if unavailable)
- Load percent, memory used/total, temperature — per GPU via `/api/gpu`

**Anomaly**
- `system_anomaly_detected` gauge — fires when current sample is anomalous relative to the trained model

**Exporter health**
- `exporter_up` — 1 if the agent is reachable

Full Prometheus exposition at `/metrics`. REST snapshot at `/api/*`. Interactive docs at `/docs`.

---

## Alerting

`alert_rules.yml` defines threshold alerts for CPU, memory, and disk, an exporter-down alert, and an `AnomalousSystemBehavior` alert wired to `system_anomaly_detected`. Rules evaluate and appear at Prometheus's `/alerts` without Alertmanager — Alertmanager is only needed for routing to email, Slack, or a webhook. A reference config is in `alertmanager.yml`.

---

## Anomaly Detection

`net_observer.py` implements a `NetworkObserver` that trains an `IsolationForest` online on CPU/memory/network samples collected during each Prometheus scrape. Once 50 samples have been observed, `/api/anomaly` and the `system_anomaly_detected` gauge report whether the current sample is anomalous relative to the model. The alert fires off that gauge like any threshold rule.

Known limitation: the model resets on restart. Persisting to disk and retraining on a rolling window is the next planned improvement.

---

## Running

**Full stack (exporter + Prometheus + Alertmanager + Grafana):**

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Exporter API / Swagger | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |
| Grafana | http://localhost:3000 (admin/admin) |

**Exporter only:**

```bash
docker run -p 8000:8000 sys-exp
# or
pip install -r requirements.txt && python main.py --port 8000
```

Tear down: `docker compose down` (add `-v` to drop Prometheus and Grafana data volumes).

---

## Multi-Device Setup (Tailscale)

Each device runs its own agent. Prometheus aggregates by scraping multiple targets under the `local-agent` job — no extra component needed. For cross-device monitoring without exposing LAN IPs, agents bind to their Tailscale address; Prometheus scrapes over the Tailscale network.

```yaml
# prometheus.yml — add one entry per device
- job_name: "local-agent"
  static_configs:
    - targets:
        - "localhost:8000"        # this machine
        - "100.x.x.x:8000"       # second laptop via Tailscale
        - "100.x.x.x:8000"       # third device via Tailscale
```

A commented example is included in `prometheus.yml`.

---

## Docker Networking Note

Two `prometheus.yml` variants are intentionally included:

| File | Used when |
|---|---|
| `prometheus.yml` | Running services directly on the host — scrapes `localhost:8000` |
| `docker/prometheus.yml` | Docker Compose stack — scrapes `exporter:8000` (containers address each other by service name) |

Both are identical except for target hostnames.

---

## Project Structure

| File | Purpose |
|---|---|
| `main.py` | FastAPI app — `/metrics`, `/api/*` endpoints, Prometheus gauges |
| `metrics.py` | Cross-platform metric collection via psutil/GPUtil |
| `net_observer.py` | `IsolationForest` anomaly detector |
| `prometheus.yml` | Prometheus config for native (host) mode |
| `docker/prometheus.yml` | Prometheus config for Docker Compose mode |
| `alert_rules.yml` | Alerting rules — CPU/memory/disk thresholds, exporter down, anomaly |
| `alertmanager.yml` | Reference Alertmanager routing config |
| `Dockerfile` | Builds the exporter as a standalone image |
| `docker-compose.yml` | Full stack: exporter + Prometheus + Alertmanager + Grafana |
| `requirements.txt` | Python dependencies |

---

## Long-Term Storage

By default Prometheus retains samples only for its local retention window. For long-term trend analysis, uncomment the `remote_write` block in `prometheus.yml` and point it at a remote-write-compatible backend — [VictoriaMetrics](https://victoriametrics.com/) single-node is a one-line Docker run, or Thanos Receive for a multi-instance setup.

---

## What's Next

- [ ] Persist the trained `IsolationForest` model to disk; retrain on a rolling window instead of resetting at restart
- [ ] File- or DNS-based Prometheus service discovery (currently targets are added manually)
- [ ] HPA integration if deployed to Kubernetes
