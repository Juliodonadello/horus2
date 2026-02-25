# Horus IoT Platform - Base Project (Python)

Proyecto base para la plataforma de monitoreo de baterías **Horus**.
- Comunicación **HTTP** entre edge y backend.
- Almacenamiento: **InfluxDB** (series temporales) y **PostgreSQL** (eventos/metadatos).
- Orquestación: **Docker Compose**.
- Visualización: **Grafana** con dashboards pre-configurados.

## Contenido
- `sensors/` : interfaces y sensores simulados para desarrollo en edge.
- `edge/` : colector que envía lecturas por HTTP al backend.
- `backend/` : FastAPI app que recibe lecturas y las persiste en InfluxDB y PostgreSQL.
- `frontend/grafana/` : dashboards y provisioning para Grafana.
- `docker-compose.yml` : servicios para desarrollo: backend, influxdb, postgres, grafana.

## Requisitos
- Docker & Docker Compose (v1.29+ o compatible)

## Levantar el entorno
```bash
docker-compose up --build
```
- **Backend**: http://localhost:8000
- **Grafana**: http://localhost:3000 (usuario: `admin`, contraseña: `admin`)
- **InfluxDB**: http://localhost:8086 (usuario: `admin`, contraseña: `adminpassword`)
- **PostgreSQL**: localhost:5432 (usuario: `horus_user`, contraseña: `horus_pass`)

## API Endpoints

### POST `/ingest`
Recibe lecturas de sensores del edge device.

**Payload Example:**
```json
{
  "site_id": "site_001",
  "timestamp": 1707000000,
  "readings": [
    {"sensor": "voltage_sim", "type": "voltage", "value": 12.5},
    {"sensor": "current_sim", "type": "current", "value": 2.3}
  ]
}
```

**Response:**
```json
{
  "status": "ok",
  "readings_count": 2
}
```

### GET `/health`
Verifica la salud de los servicios (InfluxDB y PostgreSQL).

**Response:**
```json
{
  "status": "ok",
  "influxdb": "ok",
  "postgres": "ok"
}
```

## Grafana Dashboards

### Power Monitoring Dashboard
Dashboard principal que incluye:
- **Latest Voltage / Current**: Gauges con últimos valores
- **Voltage Over Time**: Serie temporal del voltaje (últimas 24h)
- **Current Over Time**: Serie temporal de corriente (últimas 24h)
- **Estimated Power (W)**: Potencia calculada (V × I)
- **Recent Events**: Tabla con eventos recientes desde PostgreSQL

**Datasources configurados:**
- InfluxDB: Para series temporales de sensores
- PostgreSQL: Para tabla de eventos

## Probar el edge simulator
En otra terminal (o en la Raspberry Pi), entrar a `edge/` y ejecutar:
```bash
python3 collector.py
```

**Variables de entorno para edge:**
```bash
BACKEND_URL=http://backend:8000/ingest  # URL del backend
INTERVAL=5                                # Intervalo entre envíos (segundos)
SITE_ID=site_001                         # Identificador del sitio
```

Esto enviará lecturas cada 5 segundos con reintentos automáticos en caso de error.

## Estructura de datos

### InfluxDB (horus-bucket)
Measurement: `sensor_readings`
- **Tags**: `site_id`, `sensor`, `type`
- **Fields**: `value` (float)
- **Timestamp**: Segundos desde epoch

### PostgreSQL (events table)
```sql
CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  site_id TEXT,
  ts TIMESTAMP,
  readings JSONB
)
```

## Notas de configuración

- Las credenciales se encuentran en `docker-compose.yml`. **Para producción**, reemplazar por secretos.
- El proyecto es **agnóstico** a los sensores: implementar la interfaz `ISensor` en `sensors/base.py` y añadir nuevos sensores.
- Los sensores simulados (`VoltageSensor`, `CurrentSensor`) ahora usan random walk para comportamiento más realista.

## Generate architecture image (Python)

A Python script can generate a simple architecture JPG without external Node tools.

Prerequisite: install Pillow:

```bash
pip install pillow
```

Run:

```bash
python scripts/generate_architecture.py
```

This writes `docs/architecture.jpg`.

## Mejoras recientes

- ✅ Arreglada indentación de Point creation en backend
- ✅ Agregado datasource de PostgreSQL a Grafana
- ✅ Dashboard completamente rediseñado con 6 paneles:
  - 2 gauges (últimas lecturas)
  - 2 gráficas de serie temporal (V, I)
  - 1 gráfica de potencia calculada
  - 1 tabla de eventos desde PostgreSQL
- ✅ Mejor logging y manejo de errores en backend y edge
- ✅ Sensores mejorados con random walk para realismo
- ✅ Health check mejorado (verifica ambas bases de datos)

## Troubleshooting

**El dashboard no muestra datos:**
1. Verificar que el backend está recibiendo lecturas: `docker logs horus-backend`
2. Verificar conectividad de Grafana a InfluxDB: Grafana → Data Sources → InfluxDB
3. Verificar que existen datos en InfluxDB: InfluxDB UI → Explore
4. Reiniciar el contenedor de Grafana: `docker-compose restart grafana`

**Error de conexión a PostgreSQL:**
1. Verificar que postgres está corriendo: `docker-compose ps`
2. Verificar credenciales en `docker-compose.yml`
3. Verificar que la tabla `events` existe: `docker exec horus-postgres psql -U horus_user -d horus -c "\dt"`
#
