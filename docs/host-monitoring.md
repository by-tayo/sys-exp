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
