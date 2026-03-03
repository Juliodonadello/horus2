import os, logging
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from influxdb_client import InfluxDBClient, Point, WritePrecision
import psycopg2
import time
import random
import threading

logging.basicConfig(level=logging.INFO)
app = FastAPI(title='Horus Backend')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

INFLUX_URL = os.environ.get('INFLUX_URL', 'http://influxdb:8086')
INFLUX_TOKEN = os.environ.get('INFLUX_TOKEN', 'my-influx-token')
INFLUX_ORG = os.environ.get('INFLUX_ORG', 'horus-org')
INFLUX_BUCKET = os.environ.get('INFLUX_BUCKET', 'horus-bucket')

POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'postgres')
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'horus')
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'horus_user')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'horus_pass')

# Initialize InfluxDB client (lazy)
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api()

SIM_SCENARIOS: Dict[str, Dict[str, float]] = {
    'stable_day': {
        'description': 'Operación estable con baja variación.',
        'voltage_base': 49.8,
        'current_base': 2.7,
        'temp_base': 30.0,
        'irr_base': 580.0,
        'soc_base': 78.0,
        'noise': 0.2,
    },
    'peak_solar': {
        'description': 'Alta irradiancia y carga moderada.',
        'voltage_base': 51.4,
        'current_base': 3.4,
        'temp_base': 33.0,
        'irr_base': 930.0,
        'soc_base': 84.0,
        'noise': 0.35,
    },
    'storm_event': {
        'description': 'Evento con nubosidad y caídas abruptas.',
        'voltage_base': 47.6,
        'current_base': 1.6,
        'temp_base': 25.0,
        'irr_base': 180.0,
        'soc_base': 62.0,
        'noise': 0.75,
    },
    'stress_test': {
        'description': 'Oscilaciones severas para validar alertas.',
        'voltage_base': 48.8,
        'current_base': 4.1,
        'temp_base': 36.0,
        'irr_base': 520.0,
        'soc_base': 55.0,
        'noise': 1.1,
    },
}


class SimulationRun(BaseModel):
    run_id: str
    scenario: str
    site_id: str
    interval_seconds: float = 2.0
    duration_seconds: int = 120


class SimulationManager:
    def __init__(self):
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def start_run(self, payload: SimulationRun):
        if payload.scenario not in SIM_SCENARIOS:
            raise HTTPException(status_code=404, detail='Scenario not found')

        with self._lock:
            if payload.run_id in self._runs:
                raise HTTPException(status_code=409, detail='run_id already exists')
            stop_event = threading.Event()
            state = {
                'run_id': payload.run_id,
                'scenario': payload.scenario,
                'site_id': payload.site_id,
                'interval_seconds': payload.interval_seconds,
                'duration_seconds': payload.duration_seconds,
                'started_at': int(time.time()),
                'points_written': 0,
                'status': 'running',
                'stop_event': stop_event,
                'thread': None,
            }
            self._runs[payload.run_id] = state
            t = threading.Thread(target=self._run_worker, args=(payload.run_id,), daemon=True)
            state['thread'] = t
            t.start()

    def _run_worker(self, run_id: str):
        with self._lock:
            state = self._runs.get(run_id)
        if not state:
            return

        scenario = SIM_SCENARIOS[state['scenario']]
        stop_event = state['stop_event']
        interval_seconds = float(state['interval_seconds'])
        duration_seconds = int(state['duration_seconds'])
        max_loops = max(1, int(duration_seconds / max(interval_seconds, 0.5)))

        for index in range(max_loops):
            if stop_event.is_set():
                break

            wave = (index % 20) / 20.0
            readings = self._build_readings(state['site_id'], scenario, wave)
            try:
                ingest(
                    IngestPayload(
                        site_id=state['site_id'],
                        timestamp=int(time.time()),
                        readings=[Reading(**r) for r in readings],
                    )
                )
                with self._lock:
                    if run_id in self._runs:
                        self._runs[run_id]['points_written'] += len(readings)
            except Exception as e:
                logging.error('Simulation run %s failed writing data: %s', run_id, e)

            time.sleep(interval_seconds)

        with self._lock:
            if run_id in self._runs:
                self._runs[run_id]['status'] = 'stopped' if stop_event.is_set() else 'completed'
                self._runs[run_id]['finished_at'] = int(time.time())

    def _build_readings(self, site_id: str, scenario: Dict[str, float], wave: float):
        noise = scenario['noise']
        voltage = round(scenario['voltage_base'] + ((wave - 0.5) * 2.2) + random.uniform(-noise, noise), 3)
        current = round(scenario['current_base'] + ((0.5 - wave) * 1.3) + random.uniform(-noise, noise), 3)
        temperature = round(scenario['temp_base'] + random.uniform(-noise * 2, noise * 2), 3)
        irradiance = round(max(0.0, scenario['irr_base'] + (wave * 120) + random.uniform(-noise * 30, noise * 30)), 3)
        soc = round(min(100.0, max(5.0, scenario['soc_base'] + random.uniform(-noise * 1.5, noise * 1.5))), 3)
        power = round(voltage * current, 3)

        return [
            {'sensor': f'voltage_{site_id}_sim', 'type': 'voltage', 'value': voltage},
            {'sensor': f'current_{site_id}_sim', 'type': 'current', 'value': current},
            {'sensor': f'power_{site_id}_sim', 'type': 'power', 'value': power},
            {'sensor': f'temp_{site_id}_sim', 'type': 'temperature', 'value': temperature},
            {'sensor': f'irr_{site_id}_sim', 'type': 'irradiance', 'value': irradiance},
            {'sensor': f'soc_{site_id}_sim', 'type': 'soc', 'value': soc},
        ]

    def stop_run(self, run_id: str):
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise HTTPException(status_code=404, detail='run_id not found')
            run['stop_event'].set()
            run['status'] = 'stopping'

    def status(self):
        with self._lock:
            return [
                {k: v for k, v in run.items() if k not in ('thread', 'stop_event')}
                for run in self._runs.values()
            ]


simulation_manager = SimulationManager()

def get_pg_conn():
    return psycopg2.connect(host=POSTGRES_HOST, dbname=POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD)

def init_pg_schema():
    """Initialize PostgreSQL schema on startup."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                site_id TEXT,
                ts TIMESTAMP,
                readings JSONB
            )
        """)
        conn.commit()
        logging.info('PostgreSQL schema initialized')
        cur.close()
        conn.close()
    except Exception as e:
        logging.error('Failed to initialize PostgreSQL schema: %s', e)

class Reading(BaseModel):
    sensor: str
    type: str
    value: float

class IngestPayload(BaseModel):
    site_id: str
    timestamp: int
    readings: List[Reading]

@app.on_event("startup")
def startup_event():
    """Initialize schema and check connectivity on startup."""
    init_pg_schema()
    logging.info('Backend service started')


app.mount('/app', StaticFiles(directory='static', html=True), name='app')

@app.post('/ingest')
def ingest(payload: IngestPayload):
    """Ingest sensor readings into InfluxDB and PostgreSQL."""
    # write readings to InfluxDB
    try:
        for r in payload.readings:
            p = (Point('sensor_readings')
                 .tag('site_id', payload.site_id)
                 .tag('sensor', r.sensor)
                 .tag('type', r.type)
                 .field('value', float(r.value))
                 .time(payload.timestamp, WritePrecision.S))
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
        logging.debug('Wrote %d points to InfluxDB for site %s', len(payload.readings), payload.site_id)
    except Exception as e:
        logging.exception('InfluxDB write error: %s', e)
        raise HTTPException(status_code=500, detail='InfluxDB write failed')

    # insert event row into Postgres
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (site_id, ts, readings) VALUES (%s, to_timestamp(%s), %s)",
            (payload.site_id, payload.timestamp, json.dumps([r.dict() for r in payload.readings]))
        )
        conn.commit()
        cur.close()
        conn.close()
        logging.debug('Event recorded in PostgreSQL for site %s', payload.site_id)
    except Exception as e:
        logging.error('PostgreSQL write error: %s', e)
        # Non-fatal for ingest - continue but log
    
    return {'status': 'ok', 'readings_count': len(payload.readings)}


@app.get('/')
def root_app():
    return FileResponse('static/index.html')


@app.get('/simulation/scenarios')
def simulation_scenarios():
    return {'scenarios': SIM_SCENARIOS}


@app.post('/simulation/start')
def simulation_start(payload: SimulationRun):
    simulation_manager.start_run(payload)
    return {'status': 'started', 'run_id': payload.run_id}


@app.post('/simulation/stop/{run_id}')
def simulation_stop(run_id: str):
    simulation_manager.stop_run(run_id)
    return {'status': 'stopping', 'run_id': run_id}


@app.get('/simulation/status')
def simulation_status():
    return {'runs': simulation_manager.status()}


@app.get('/health')
def health():
    """Health check: verifies both InfluxDB and PostgreSQL connectivity."""
    health_status = {
        'status': 'ok',
        'influxdb': 'unknown',
        'postgres': 'unknown'
    }
    
    # Check PostgreSQL
    try:
        conn = get_pg_conn()
        conn.close()
        health_status['postgres'] = 'ok'
    except Exception as e:
        logging.error('PostgreSQL health check failed: %s', e)
        health_status['postgres'] = 'error'
        health_status['status'] = 'degraded'
    
    # Check InfluxDB
    try:
        influx_client.health()
        health_status['influxdb'] = 'ok'
    except Exception as e:
        logging.error('InfluxDB health check failed: %s', e)
        health_status['influxdb'] = 'error'
        health_status['status'] = 'degraded'
    
    status_code = 200 if health_status['status'] == 'ok' else 503
    if status_code == 503:
        raise HTTPException(status_code=status_code, detail=health_status)
    return health_status
