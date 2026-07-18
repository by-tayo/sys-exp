# System Information Exporter

## Project Overview

This project demonstrates a complete system monitoring platform for collecting, visualizing, and analyzing system metrics from a single device. It leverages Prometheus for metrics collection, Python agents to expose system stats via HTTP, and optionally uses Tailscale VPN for secure cross-device monitoring.

The application showcases modern DevOps and monitoring practices, including system metric collection, container-friendly design, and secure private network integration.


---

## Goals & Objectives

### Primary Goals

* Build a functional system monitoring platform across multiple laptops.
* Collect metrics including CPU, memory, disk, network, and process usage.
* Deploy Prometheus to scrape metrics from distributed agents.
* Ensure data privacy using localhost and/or Tailscale VPN connections.
* Export and gather metrics through customized visualizations in Grafana dashboards.

### Learning Objectives

* Gain hands-on experience with Prometheus and Python metric exporters.
* Understand monitoring agent design and metric exposure with Flask.
* Learn how to securely collect metrics across devices without exposing sensitive IP addresses.
* Explore DevOps workflows for system observability.

---

## Tools & Technologies Used

### Development

* Python: Programming language for building the monitoring agents.
* Flask: Lightweight web framework to expose system metrics via HTTP.
* Flasgger: Adds Swagger UI documentation for the agent APIs.
* Command Prompt (CMD): Windows terminal used for running Python scripts, Prometheus, and system commands.

### Monitoring & Observability

* Prometheus: Open-source monitoring system for collecting and storing time-series metrics.
* Prometheus Python Client: Python library to expose system metrics in Prometheus-compatible format.
* Grafana: Dashboard for visualizing metrics in real-time.

### Networking & Security

* localhost: Localhost metric endpoints for agent testing and privacy.

DevOps Practices

* YAML: Configuration language for Prometheus scrape configs.
* Infrastructure as Code (IaC): Declarative configuration of Prometheus targets and agent labels.

---
## FastAPI, Prometheus, and Grafana specs

![FastAPI Main Page](images/main_api.png)
![System Health](images/sys_health.png)
![System Process](images/sys_process.png)
![System Status](images/sys_status.png)
![Prometheus Targets](images/prometh_targets.png)
![Grafana Visualization](images/grafana_visualizations.png)

## Key Takeaways

### Technical Skills Developed

* A single device monitoring with Prometheus.
* Python-based system metric collection and API design.
* Prometheus configuration for multiple targets and labels.

### Challenges

* Ensuring metrics collection across laptops without exposing sensitive network information.
* Configuring Prometheus to scrape multiple agents on different devices.
* Handling multiple ports and secure agent connections using Tailscale.

---

## Alerting

`alert_rules.yml` defines Prometheus alerting rules for CPU, memory, and disk
thresholds, exporter downtime, and anomalous behavior (see below). Prometheus
is configured (`prometheus.yml`) to evaluate these rules and send firing
alerts to Alertmanager on `localhost:9093`. Rules evaluate and appear under
Prometheus's `/alerts` page even without Alertmanager running — Alertmanager
is only needed if you want alerts routed somewhere (email, Slack, a webhook).
A reference config is provided in `alertmanager.yml`; fill in a real receiver
and run `alertmanager --config.file=alertmanager.yml` alongside Prometheus.

## GPU & Process Metrics

* GPU load, memory used/total, and temperature are exposed per-GPU via
  `/api/gpu` and the `system_gpu_*` Prometheus gauges, using
  [GPUtil](https://github.com/anderskm/gputil) (NVIDIA GPUs only). On
  machines without a supported GPU or without GPUtil installed, this
  degrades gracefully to an empty list rather than erroring.
* `/api/processes` now also returns each process's RSS memory, thread count,
  and status, in addition to CPU/memory percent.

## Anomaly Detection

The `IsolationForest`-based `NetworkObserver` (`net_observer.py`) trains
online on CPU/memory/network samples collected during Prometheus scrapes.
Once at least 50 samples have been observed, `/api/anomaly` and the
`system_anomaly_detected` gauge report whether the current sample looks
anomalous relative to the model. The `AnomalousSystemBehavior` alert in
`alert_rules.yml` fires off that gauge like any other threshold alert.

## Cross-Platform Support

The exporter runs on Windows, Linux, and macOS. Disk usage resolves the
system drive root per-OS (`C:\` on Windows, `/` on Linux/macOS) instead of
hardcoding a Windows path, and the reported hostname comes from
`socket.gethostname()` rather than a fixed string.

## Long-Term Metric Storage

By default Prometheus only retains samples locally for its configured
retention window. To keep history for long-term trend analysis, uncomment
the `remote_write` block in `prometheus.yml` and point it at a
remote-write-compatible backend such as
[VictoriaMetrics](https://victoriametrics.com/) (single-node is a one-line
Docker run) or Thanos Receive.

## Multi-Device / Distributed Monitoring

Prometheus aggregates metrics from multiple laptops by scraping multiple
targets under the same job — this is the mechanism behind the "multiple
laptops" goal above, no extra component needed. Run `python main.py --port
<port>` on each machine (optionally reachable over Tailscale for privacy),
then add one `static_configs` entry per machine to the `local-agent` job in
`prometheus.yml`; a commented example is included there.

---

## Future Enhancements

### Recently Implemented

* ✅ Prometheus alerting rules for CPU, memory, and disk thresholds.
* ✅ GPU and process-level metrics.
* ✅ Anomaly detection wired up to a metric/endpoint/alert.
* ✅ Multi-platform (Windows/Linux/macOS) agent support.
* ✅ Long-term metric storage via optional remote_write.
* ✅ Documented multi-device aggregation via Prometheus multi-target scraping.

### Remaining Medium-Term Work

* Dynamic agent discovery and auto-registration in Prometheus (currently
  targets are added manually to `prometheus.yml`; Prometheus supports file-
  or DNS-based service discovery for this).
* Horizontal Pod Autoscaler (HPA) integration if deployed in Kubernetes —
  not attempted here since it requires an actual cluster to build and test
  against.

### Remaining Long-Term Goals

* True distributed aggregation beyond Prometheus's built-in multi-target
  scraping (e.g. Thanos/Cortex-style global query view across multiple
  independent Prometheus instances), if the project ever needs more than a
  handful of devices.
* Persisting the trained IsolationForest model to disk (so it survives
  restarts) and retraining it on a rolling window instead of only once at
  50 samples.
