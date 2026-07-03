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

## Future Enhancements

### Short-Term Improvements

* Implement Prometheus alerting rules for CPU, memory, or disk thresholds.
* Expand agent metrics to include GPU and process-level insights.

### Medium-Term Features

* Dynamic agent discovery and auto-registration in Prometheus.
* Persistent storage of metrics for long-term trend analysis.
* Horizontal Pod Autoscaler (HPA) integration if deployed in Kubernetes.

### Long-Term Goals

* Multi-platform agent support (Linux, macOS).
* Distributed system monitoring with centralized aggregation.
* Machine learning-based anomaly detection and alerting.
