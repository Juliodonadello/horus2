from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import datetime

app = FastAPI()

# Mocked databases
postgres_db = []
influxdb_db = []

class SensorReading(BaseModel):
    sensor_name: str
    sensor_type: str
    value: float
    timestamp: datetime.datetime

@app.post("/sensors/")
async def create_sensor_reading(reading: SensorReading):
    # Simulate storing in PostgreSQL
    postgres_db.append(reading.model_dump())

    # Simulate storing in InfluxDB
    influxdb_db.append({
        "measurement": reading.sensor_type,
        "tags": {"sensor_name": reading.sensor_name},
        "fields": {"value": reading.value},
        "time": reading.timestamp
    })

    return {"message": "Sensor reading stored successfully"}

@app.get("/sensors/postgres/")
async def get_postgres_readings():
    return postgres_db

@app.get("/sensors/influxdb/")
async def get_influxdb_readings():
    return influxdb_db
