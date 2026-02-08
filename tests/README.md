# Test nodes

Use the node simulator to generate test traffic to the backend and populate InfluxDB/Postgres.

From the repo root run (requires Python and `requests` installed):

```powershell
python tests/nodes/node_simulator.py --nodes 3 --interval 5 --backend http://localhost:8000/ingest
```

Or run inside Docker Compose by starting the `edge_sim` service which runs `edge/collector.py`.
