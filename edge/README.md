# Edge

`edge/` contiene el simulador principal del proyecto. Desde aca se generan payloads de telemetria y estado compatibles con el backend.

## Que hace

El colector `edge.collector` simula multiples localidades y envia:

- `POST /ingest/telemetry`
- `POST /ingest/status`

Cada ciclo produce mediciones de corriente y voltaje, junto con un snapshot de estado con alarmas derivadas de esos valores.

## Ejecutarlo localmente o por fuera del stack

```bash
python -m edge.collector
```

Si el backend corre con `docker-compose`, usa `http://localhost:8000` como base para enviar los payloads al servicio expuesto.

Para correr un perfil puntual en PowerShell:

```bash
$env:SIMULATION_PROFILE="storm_front"; python -m edge.collector
```

Para limitar la simulacion a algunas localidades:

```bash
$env:SIMULATION_TARGETS="cordoba_capital,rio_cuarto"; python -m edge.collector
```

## Variables de entorno

- `BACKEND_BASE_URL`: base del backend. Default: `http://localhost:8000`
- `BACKEND_TELEMETRY_URL`: endpoint de telemetria. Default: `http://localhost:8000/ingest/telemetry`
- `BACKEND_STATUS_URL`: endpoint de estado. Default: `http://localhost:8000/ingest/status`
- `INTERVAL`: segundos entre envios. Default: `5`
- `SENSOR_VERSION`: version reportada por el simulador. Default: `sim-edge-2.1.0`
- `SIMULATION_PROFILE`: perfil de simulacion activo. Default: `steady_day`
- `SIMULATION_TARGETS`: lista separada por comas o `all`. Default: `all`

## Perfiles disponibles

- `steady_day`: operacion estable con oscilaciones suaves durante el dia
- `cloudy_swings`: nubes intermitentes con caidas y recuperaciones rapidas
- `storm_front`: tension baja y alarmas frecuentes
- `critical_load`: alta demanda con corriente elevada y picos de potencia
- `night_watch`: operacion nocturna con baja corriente y tension mas estable

## Localidades simuladas

- `cordoba_capital`
- `villa_carlos_paz`
- `rio_cuarto`
- `villa_maria`
- `san_francisco`
- `alta_gracia`
- `jesus_maria`
- `bell_ville`

## Dependencias

`edge/requirements.txt` instala:

- `requests`

El simulador reutiliza modulos compartidos del repo, como `sensors/`.
