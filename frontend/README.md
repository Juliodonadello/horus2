# Frontend (Grafana)

This folder contains Grafana provisioning and sample dashboards for the Horus project.

How to use

- The top-level `docker-compose.yml` already defines a `grafana` service. This repository mounts the following host folders into the Grafana container:
  - `./frontend/grafana/provisioning` -> `/etc/grafana/provisioning`
  - `./frontend/grafana/dashboards` -> `/var/lib/grafana/dashboards`

- To start the stack (from repo root):

```powershell
docker compose up -d
```

- Grafana will be available at http://localhost:3000 (default admin/admin).
- Update the InfluxDB token either in `docker-compose.yml` environment (`INFLUXDB_INIT_ADMIN_TOKEN`) or by updating `frontend/grafana/provisioning/datasources/datasources.yaml`.

Next steps

- Add real dashboards JSON files inside `frontend/grafana/dashboards/`.
- Adjust datasource `token` in `datasources.yaml` to use a secret or environment-based approach.
