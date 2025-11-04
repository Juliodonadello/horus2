import os, logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from influxdb_client import InfluxDBClient, Point, WritePrecision
import psycopg2
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

class Reading(BaseModel):
    sensor: str
    type: str
    value: float

class IngestPayload(BaseModel):
    site_id: str
    timestamp: int
    readings: List[Reading]

@app.post('/ingest')
def ingest(payload: IngestPayload):
    # write readings to InfluxDB
    try:
        for r in payload.readings:
            p = Point('sensor_readings')                        .tag('site_id', payload.site_id)                        .tag('sensor', r.sensor)                        .tag('type', r.type)                        .field('value', float(r.value))                        .time(payload.timestamp, WritePrecision.S)
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
        logging.info('Wrote %d points to InfluxDB', len(payload.readings))
    except Exception as e:
        logging.exception('Influx error: %s', e)
        raise HTTPException(status_code=500, detail='InfluxDB write failed')

    # insert a simple event row into Postgres
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
        cur.execute(
            "INSERT INTO events (site_id, ts, readings) VALUES (%s, to_timestamp(%s), %s)",
            (payload.site_id, payload.timestamp, json.dumps([r.dict() for r in payload.readings]))
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logging.exception('Postgres error: %s', e)
        # Non-fatal for ingest - return success but log
    return {'status': 'ok'}
