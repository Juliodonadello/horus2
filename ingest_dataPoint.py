import requests

r = requests.post("http://localhost:8000/ingest", json={
    "site_id": "test_site",
    "timestamp": 1761699600,
    "readings": [
        {"sensor": "volt_test", "type": "voltage", "value": 12.45},
        {"sensor": "curr_test", "type": "current", "value": 1.23}
    ]
})
print(r.status_code, r.text)
