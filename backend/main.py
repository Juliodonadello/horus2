import os, logging
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from influxdb_client import InfluxDBClient, Point, WritePrecision
import psycopg2
from psycopg2.extras import RealDictCursor
import time

logging.basicConfig(level=logging.INFO)
app = FastAPI(title='Horus Backend')

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
