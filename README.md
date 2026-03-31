# Horus IoT Platform - Base Project (Python)

Proyecto base para la plataforma de monitoreo de baterias **Horus**.
- Comunicacion **HTTP** entre edge y backend.
- Almacenamiento: **InfluxDB** para telemetria y **PostgreSQL** para snapshots de estado y alarmas.
- Orquestacion: **Docker Compose**.
- Visualizacion: **Grafana** con dashboards preconfigurados.

## Contenido
- `sensors/`: utilidades de sensores simulados.
- `edge/`: simulador externo que genera telemetria y status compatibles con el backend.
- `backend/`: app FastAPI que recibe payloads y los persiste en InfluxDB y PostgreSQL.
- `frontend/grafana/`: dashboards y provisioning para Grafana.
- `docker-compose.yml`: servicios para desarrollo local.

## Requisitos
- Docker y Docker Compose

## Levantar el entorno base
```bash
docker-compose up --build
```

Ese comando levanta:
- `backend`
- `influxdb`
- `postgres`
- `grafana`

El `Edge Simulator` ya no forma parte de `docker-compose.yml`. Si queres generar datos simulados, ejecutalo por fuera del stack apuntando al backend.

Accesos:
- Backend + Horus Control Center: `http://localhost:8000`
- Grafana: `http://localhost:3000` (`admin` / `admin`)
- InfluxDB: `http://localhost:8086` (`admin` / `adminpassword`)
- PostgreSQL: `localhost:5432` (`horus_user` / `horus_pass`)

## Ejecutar simulaciones por fuera del stack

El simulador se corre de forma externa al stack principal. Desde el repo, por ejemplo:

```bash
python -m edge.collector
```

Si el backend corre con `docker-compose`, usa `localhost` en las URLs del simulador para publicar contra el puerto expuesto `8000`.

Variables de entorno relevantes:

```bash
BACKEND_BASE_URL=http://localhost:8000
BACKEND_TELEMETRY_URL=http://localhost:8000/ingest/telemetry
BACKEND_STATUS_URL=http://localhost:8000/ingest/status
INTERVAL=5
SENSOR_VERSION=sim-edge-2.1.0
SIMULATION_PROFILE=steady_day
SIMULATION_TARGETS=all
```

Perfiles disponibles en el simulador:
- `steady_day`: operacion estable con oscilaciones suaves.
- `cloudy_swings`: nubes intermitentes con caidas y recuperaciones.
- `storm_front`: tension baja y alarmas mas frecuentes.
- `critical_load`: corriente elevada y picos de potencia.
- `night_watch`: operacion nocturna con baja corriente.

Para lanzar un perfil puntual:

```bash
$env:SIMULATION_PROFILE="storm_front"; python -m edge.collector
```

Para limitar la simulacion a algunas localidades:

```bash
$env:SIMULATION_TARGETS="cordoba_capital,rio_cuarto"; python -m edge.collector
```

Localidades simuladas actualmente:
- `cordoba_capital`
- `villa_carlos_paz`
- `rio_cuarto`
- `villa_maria`
- `san_francisco`
- `alta_gracia`
- `jesus_maria`
- `bell_ville`

## API Endpoints

### POST `/ingest/telemetry`
Recibe telemetria instantanea del dispositivo y la persiste en InfluxDB.

Payload ejemplo:
```json
{
  "device_id": "cordoba_capital",
  "timestamp": 1742893200,
  "measurements": {
    "ch1_current": 12.34,
    "ch2_current": 10.91,
    "ch3_voltage": 48.21,
    "ch4_voltage": 47.88
  }
}
```

Consulta Flux de ejemplo para validar escrituras sin hardcodear una localidad:

```flux
from(bucket: "horus-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> group(columns: ["device_id"])
  |> last()
```

Response:
```json
{
  "status": "ok",
  "device_id": "cordoba_capital",
  "timestamp": 1742893200
}
```

Reglas:
- `device_id`: string obligatorio
- `timestamp`: epoch UTC en segundos, obligatorio
- `measurements`: objeto obligatorio y no vacio
- todos los valores de `measurements` deben ser numericos

### POST `/ingest/status`
Recibe snapshots de estado del dispositivo y los persiste en PostgreSQL.

Payload ejemplo:
```json
{
  "device_id": "cordoba_capital",
  "timestamp": 1742893200,
  "fw_version": "sim-edge-2.1.0-steady_day",
  "ip": "127.0.0.1",
  "uptime_ms": 1234567,
  "alarms": {
    "ch1_max": false,
    "ch1_min": false,
    "ch2_max": false,
    "ch2_min": false,
    "ch3_max": false,
    "ch3_min": false,
    "ch4_max": false,
    "ch4_min": false
  }
}
```

Response:
```json
{
  "status": "ok",
  "device_id": "cordoba_capital",
  "stored": true
}
```

Reglas:
- `device_id`: string obligatorio
- `timestamp`: epoch UTC en segundos, obligatorio
- `fw_version`: string obligatorio
- `ip`: IP valida obligatoria
- `uptime_ms`: integer obligatorio
- `alarms`: objeto obligatorio y no vacio
- todos los valores de `alarms` deben ser boolean

### GET `/health`
Verifica la salud de InfluxDB y PostgreSQL.

## Grafana Dashboards

La portada del backend ya no muestra controles de simulacion. Solo embebe dos dashboards de Grafana:
- Dashboard operacional
- Dashboard de alarmas

### Como interpretar el dashboard operacional

Los 4 gauges principales muestran una metrica general por canal:
- `Corriente continua promedio`: promedio del ultimo valor reportado por todas las localidades de Cordoba para `ch1_current`
- `Corriente alterna promedio`: promedio del ultimo valor reportado por todas las localidades de Cordoba para `ch2_current`
- `Voltaje continuo promedio`: promedio del ultimo valor reportado por todas las localidades de Cordoba para `ch3_voltage`
- `Voltaje alterno promedio`: promedio del ultimo valor reportado por todas las localidades de Cordoba para `ch4_voltage`

Semantica del payload:
- `ch1_current`: corriente continua
- `ch2_current`: corriente alterna
- `ch3_voltage`: voltaje continuo
- `ch4_voltage`: voltaje alterno

Importante:
- no es un promedio temporal de los ultimos 15 minutos
- cada gauge calcula el promedio a partir del **ultimo registro disponible** de cada localidad incluida
- cada gauge principal tiene enlace al dashboard `Horus Detalle Por Localidad`, donde se ve esa metrica abierta por localidad
- el dashboard de detalle es una vista compacta 2x2 con las cuatro metricas abiertas por localidad
- el dashboard operacional separa los historicos en 4 paneles: corriente continua, corriente alterna, voltaje continuo y voltaje alterno
- la potencia tambien se separa en 2 paneles: `potencia_dc = ch1_current * ch3_voltage` y `potencia_ac = ch2_current * ch4_voltage`
- el panel de `Ultimos snapshots de estado` fue removido del dashboard operacional para dejarlo enfocado en metricas energeticas

Rangos visuales configurados en las agujas:
- corriente continua: verde entre `1 A` y `5 A`
- corriente alterna: verde entre `0.5 A` y `4 A`
- voltaje continuo: verde entre `47 V` y `50 V`
- voltaje alterno: verde entre `200 V` y `230 V`
- cerca del limite: naranja
- fuera de rango: rojo

### Dashboard de alarmas

El dashboard `Horus Alarmas` consulta PostgreSQL y muestra:
- cantidad de localidades con alarmas activas en su ultimo estado
- cantidad de eventos de alarma en las ultimas 24 horas
- frecuencia por tipo de alarma
- ultimo estado activo por localidad
- historico persistido de eventos de alarma y descarga en CSV

### Datasources configurados
- InfluxDB: telemetria (`device_telemetry`)
- PostgreSQL: snapshots de estado (`device_status`)

## Estructura de datos

### InfluxDB (`horus-bucket`)
Measurement: `device_telemetry`
- Tags: `device_id`
- Fields: `ch1_current`, `ch2_current`, `ch3_voltage`, `ch4_voltage`
- Timestamp: timestamp recibido en UTC con precision de segundos

### PostgreSQL (`device_status`)
```sql
CREATE TABLE device_status (
  id BIGSERIAL PRIMARY KEY,
  device_id TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  fw_version TEXT NOT NULL,
  ip INET,
  uptime_ms BIGINT NOT NULL,
  alarms JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_device_status_device_ts
ON device_status (device_id, ts DESC);
```

### PostgreSQL (`alarm_events`)
Tabla persistida para historico descargable de alarmas activas.

Columnas principales:
- `device_id`
- `ts`
- `fw_version`
- `ip`
- `uptime_ms`
- `alarm_key`
- `alarm_value`
- `created_at`

## Notas de configuracion
- Las credenciales estan en `docker-compose.yml`. Para produccion, reemplazarlas por secretos.
- El backend ya no expone endpoints de simulacion ni genera escenarios por si mismo.
- El simulador `edge.collector` respeta el payload actual de InfluxDB y PostgreSQL.
- Los datos persisten mientras no se eliminen los volumenes (`docker compose down -v` si los borra).

## Generate architecture image (Python)

Prerequisito:
```bash
pip install pillow
```

Ejecutar:
```bash
python scripts/generate_architecture.py
```

Esto genera `docs/architecture.jpg`.

## Troubleshooting

**El dashboard no muestra datos**
1. Verificar que el backend esta recibiendo telemetria/status: `docker logs horus-backend`
2. Verificar que el proceso `python -m edge.collector` este corriendo si queres datos simulados
3. Verificar conectividad de Grafana a InfluxDB y PostgreSQL
4. Reiniciar Grafana: `docker-compose restart grafana`

**Quiero borrar todos los datos**
1. Ejecutar `docker compose down -v`
2. Volver a levantar con `docker compose up --build`

**Error de conexión a PostgreSQL:**
1. Verificar que postgres está corriendo: `docker-compose ps`
2. Verificar credenciales en `docker-compose.yml`
3. Verificar que la tabla `events` existe: `docker exec horus-postgres psql -U horus_user -d horus -c "\dt"`
#

## TO DO LIST

opcion1 (SNMP):
Hay un reporsitorio maestro que posee el desarrollo de las cajas con los sensores. Estos endpoints tienen un cliente de SNMP el cual es consultado por un servidor SNMP remoto para obtener datos instantaneos.
Se necesita un desarrollo que busca obtener datapoints similares a la simulación, pero que consulte mediante un servidor SNMP a los clientes SNMP que representan cada caja de sensores.

opcion2 (HTTP): 
Armar en un nuevo directorio codigo similar al simulador, que se usa acualmente en /edge, pero para deployar en placas esp32 y que le posteen las apis actuales del backend.
