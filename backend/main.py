import csv
import io
import json
import logging
import os
import time
from typing import Any, Dict

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from influxdb_client import InfluxDBClient, Point, WritePrecision
from pydantic import BaseModel, IPvAnyAddress, field_validator

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Horus Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "my-influx-token")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "horus-org")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "horus-bucket")

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "horus")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "horus_user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "horus_pass")
POSTGRES_CONNECT_RETRIES = int(os.environ.get("POSTGRES_CONNECT_RETRIES", "30"))
POSTGRES_RETRY_DELAY = float(os.environ.get("POSTGRES_RETRY_DELAY", "2"))

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api()


class TelemetryPayload(BaseModel):
    device_id: str
    site_id: str | None = None
    device_code: str | None = None
    timestamp: int
    measurements: Dict[str, float]

    @field_validator("measurements")
    @classmethod
    def validate_measurements(cls, value: Dict[str, float]) -> Dict[str, float]:
        if not value:
            raise ValueError("measurements must not be empty")
        for measurement_name, measurement_value in value.items():
            if isinstance(measurement_value, bool):
                raise ValueError(f"{measurement_name} must be numeric")
        return value


class StatusPayload(BaseModel):
    device_id: str
    site_id: str | None = None
    device_code: str | None = None
    timestamp: int
    fw_version: str
    ip: IPvAnyAddress
    uptime_ms: int
    alarms: Dict[str, bool]

    @field_validator("alarms")
    @classmethod
    def validate_alarms(cls, value: Dict[str, bool]) -> Dict[str, bool]:
        if not value:
            raise ValueError("alarms must not be empty")
        return value


def get_pg_conn():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def init_pg_schema():
    last_error: Exception | None = None

    for attempt in range(1, POSTGRES_CONNECT_RETRIES + 1):
        conn = None
        cur = None
        try:
            conn = get_pg_conn()
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS device_status (
                    id BIGSERIAL PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    site_id TEXT,
                    device_code TEXT,
                    ts TIMESTAMPTZ NOT NULL,
                    fw_version TEXT NOT NULL,
                    ip INET,
                    uptime_ms BIGINT NOT NULL,
                    alarms JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_device_status_device_ts
                ON device_status (device_id, ts DESC)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS alarm_events (
                    id BIGSERIAL PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    site_id TEXT,
                    device_code TEXT,
                    ts TIMESTAMPTZ NOT NULL,
                    fw_version TEXT NOT NULL,
                    ip INET,
                    uptime_ms BIGINT NOT NULL,
                    alarm_key TEXT NOT NULL,
                    alarm_value BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (device_id, ts, alarm_key)
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_alarm_events_ts
                ON alarm_events (ts DESC)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_alarm_events_device_ts
                ON alarm_events (device_id, ts DESC)
                """
            )
            cur.execute(
                """
                ALTER TABLE device_status
                ADD COLUMN IF NOT EXISTS site_id TEXT
                """
            )
            cur.execute(
                """
                ALTER TABLE device_status
                ADD COLUMN IF NOT EXISTS device_code TEXT
                """
            )
            cur.execute(
                """
                ALTER TABLE alarm_events
                ADD COLUMN IF NOT EXISTS site_id TEXT
                """
            )
            cur.execute(
                """
                ALTER TABLE alarm_events
                ADD COLUMN IF NOT EXISTS device_code TEXT
                """
            )
            cur.execute(
                """
                INSERT INTO alarm_events (device_id, site_id, device_code, ts, fw_version, ip, uptime_ms, alarm_key, alarm_value)
                SELECT
                    ds.device_id,
                    ds.site_id,
                    ds.device_code,
                    ds.ts,
                    ds.fw_version,
                    ds.ip,
                    ds.uptime_ms,
                    alarms.key,
                    TRUE
                FROM device_status ds
                CROSS JOIN LATERAL jsonb_each_text(ds.alarms) AS alarms(key, value)
                WHERE alarms.value = 'true'
                ON CONFLICT (device_id, ts, alarm_key) DO NOTHING
                """
            )
            conn.commit()
            logging.info("PostgreSQL schema initialized")
            return
        except Exception as exc:
            last_error = exc
            logging.warning(
                "PostgreSQL schema init attempt %s/%s failed: %s",
                attempt,
                POSTGRES_CONNECT_RETRIES,
                exc,
            )
            if conn is not None:
                conn.rollback()
            if attempt < POSTGRES_CONNECT_RETRIES:
                time.sleep(POSTGRES_RETRY_DELAY)
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

    logging.exception("Failed to initialize PostgreSQL schema after retries", exc_info=last_error)
    raise RuntimeError("PostgreSQL schema initialization failed") from last_error


def ingest_telemetry_data(payload: TelemetryPayload) -> Dict[str, Any]:
    try:
        point = Point("device_telemetry").tag("device_id", payload.device_id)
        if payload.site_id:
            point = point.tag("site_id", payload.site_id)
        if payload.device_code:
            point = point.tag("device_code", payload.device_code)
        for measurement_name, measurement_value in payload.measurements.items():
            point = point.field(measurement_name, float(measurement_value))
        point = point.time(payload.timestamp, WritePrecision.S)
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        logging.debug("Wrote telemetry for device %s", payload.device_id)
    except Exception as exc:
        logging.exception("InfluxDB write error: %s", exc)
        raise HTTPException(status_code=500, detail="InfluxDB write failed")

    return {
        "status": "ok",
        "device_id": payload.device_id,
        "timestamp": payload.timestamp,
    }


def ingest_status_data(payload: StatusPayload) -> Dict[str, Any]:
    true_alarm_keys = [alarm_key for alarm_key, is_active in payload.alarms.items() if is_active]

    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO device_status (device_id, site_id, device_code, ts, fw_version, ip, uptime_ms, alarms)
            VALUES (%s, %s, %s, to_timestamp(%s), %s, %s, %s, %s::jsonb)
            """,
            (
                payload.device_id,
                payload.site_id,
                payload.device_code,
                payload.timestamp,
                payload.fw_version,
                str(payload.ip),
                payload.uptime_ms,
                json.dumps(payload.alarms),
            ),
        )

        for alarm_key in true_alarm_keys:
            cur.execute(
                """
                INSERT INTO alarm_events (device_id, site_id, device_code, ts, fw_version, ip, uptime_ms, alarm_key, alarm_value)
                VALUES (%s, %s, %s, to_timestamp(%s), %s, %s, %s, %s, TRUE)
                ON CONFLICT (device_id, ts, alarm_key) DO NOTHING
                """,
                (
                    payload.device_id,
                    payload.site_id,
                    payload.device_code,
                    payload.timestamp,
                    payload.fw_version,
                    str(payload.ip),
                    payload.uptime_ms,
                    alarm_key,
                ),
            )

        conn.commit()
        cur.close()
        conn.close()
        logging.debug("Stored status snapshot for device %s", payload.device_id)
    except Exception as exc:
        logging.exception("PostgreSQL write error: %s", exc)
        raise HTTPException(status_code=500, detail="PostgreSQL write failed")

    return {
        "status": "ok",
        "device_id": payload.device_id,
        "stored": True,
        "active_alarm_count": len(true_alarm_keys),
    }


def build_alarm_export_csv() -> str:
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT site_id, device_code, device_id, ts, fw_version, ip::text AS ip, uptime_ms, alarm_key, alarm_value, created_at
            FROM alarm_events
            ORDER BY ts DESC, device_id ASC, alarm_key ASC
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as exc:
        logging.exception("Failed to build alarm export: %s", exc)
        raise HTTPException(status_code=500, detail="Alarm export failed")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["site_id", "device_code", "device_id", "ts", "fw_version", "ip", "uptime_ms", "alarm_key", "alarm_value", "created_at"])
    writer.writerows(rows)
    return output.getvalue()


@app.on_event("startup")
def startup_event():
    init_pg_schema()
    logging.info("Backend service started")


app.mount("/app", StaticFiles(directory="static", html=True), name="app")


@app.post("/ingest/telemetry")
def ingest_telemetry(payload: TelemetryPayload):
    return ingest_telemetry_data(payload)


@app.post("/ingest/status")
def ingest_status(payload: StatusPayload):
    return ingest_status_data(payload)


@app.get("/")
def root_app():
    return FileResponse("static/index.html")


@app.get("/alarms/export.csv")
def export_alarm_history():
    csv_content = build_alarm_export_csv()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="horus_alarm_history.csv"'},
    )


@app.get("/health")
def health():
    health_status = {
        "status": "ok",
        "influxdb": "unknown",
        "postgres": "unknown",
    }

    try:
        conn = get_pg_conn()
        conn.close()
        health_status["postgres"] = "ok"
    except Exception as exc:
        logging.error("PostgreSQL health check failed: %s", exc)
        health_status["postgres"] = "error"
        health_status["status"] = "degraded"

    try:
        influx_client.health()
        health_status["influxdb"] = "ok"
    except Exception as exc:
        logging.error("InfluxDB health check failed: %s", exc)
        health_status["influxdb"] = "error"
        health_status["status"] = "degraded"

    status_code = 200 if health_status["status"] == "ok" else 503
    if status_code == 503:
        raise HTTPException(status_code=status_code, detail=health_status)
    return health_status
