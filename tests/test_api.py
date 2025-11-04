import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import datetime

client = TestClient(app)

def test_create_sensor_reading():
    timestamp = datetime.datetime.now().isoformat()
    response = client.post("/sensors/", json={
        "sensor_name": "Test Sensor",
        "sensor_type": "Test Type",
        "value": 123.45,
        "timestamp": timestamp
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Sensor reading stored successfully"}

def test_get_postgres_readings():
    response = client.get("/sensors/postgres/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_influxdb_readings():
    response = client.get("/sensors/influxdb/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
