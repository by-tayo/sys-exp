# Monitor the host machine

The exporter reports metrics for the machine where the Python process runs.
If it runs inside Docker, it generally reports the container's view. To monitor
your full computer, run the exporter directly on that computer and let the
Dockerized Prometheus scrape it.

## 1. Start the exporter on the host

From the repository directory, install the project dependencies and start the
exporter on port 8001:

```bash
python -m pip install -r requirements.txt
python main.py --port 8001
```

## 2. Point Prometheus at it

If you're running Prometheus natively (not via Docker Compose), add a target
to the root `prometheus.yml`:

```yaml
- job_name: "local-agent"
  static_configs:
    - targets: ["localhost:8001"]
      labels:
        instance: "host-machine"
```

If you're using the Docker Compose stack instead, Prometheus runs in a
container and can't resolve `localhost:8001` as your host machine. Add a
target of `host.docker.internal:8001` to `docker/prometheus.yml` — this
works out of the box on Docker Desktop (macOS/Windows); on Linux you'll
also need to add `extra_hosts: ["host.docker.internal:host-gateway"]` to the
`prometheus` service in `docker-compose.yml`.

