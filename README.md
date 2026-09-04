# Volt Sentinel

## ESP32 → FastAPI → Dashboard

The ESP32 posts voltage and current measurements to FastAPI. FastAPI validates the payload, calculates power, keeps the latest reading per `device_id`, and marks nodes offline after `NODE_OFFLINE_TIMEOUT_SECONDS`. The React dashboard polls FastAPI every two seconds and never treats demo/waiting data as live ESP32 telemetry.

### Setup

Create `.env` from `.env.example`, then set `VITE_API_URL` to the FastAPI address that the browser can reach. On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

In a second terminal:

```powershell
npm install
npm run dev
```

Dashboard: `http://localhost:5173`  
API documentation: `http://127.0.0.1:8000/docs`

### API

- `GET /api/health` — backend availability.
- `POST /api/sensors/data` — ESP32 telemetry.
- `GET /api/nodes` — latest telemetry for each device.
- `GET /api/dashboard/summary` — calculated line status and inferred fault span.

Example ESP32 payload:

```json
{
  "device_id": "NODE_01",
  "voltage": 231.4,
  "current": 4.82
}
```

Test without hardware:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/sensors/data -Method Post -ContentType 'application/json' -Body '{"device_id":"NODE_01","voltage":231.4,"current":4.82}'
Invoke-RestMethod http://127.0.0.1:8000/api/nodes
```

Send data for additional IDs such as `NODE_02` through `NODE_15`. Nodes become `OFFLINE` only after they were previously reported and then exceed the configured timeout. The API infers a fault span from an `ONLINE → OFFLINE` adjacent pair.

### ESP32

Open [esp32/volt_sentinel_esp32.ino](esp32/volt_sentinel_esp32.ino). Set `WIFI_SSID`, `WIFI_PASSWORD`, `BACKEND_URL`, and `NODE_ID`; replace the two sensor-reading placeholders with calibrated hardware reads. Use the computer's LAN IP in `BACKEND_URL` (for example `http://192.168.1.20:8000/api/sensors/data`), not `127.0.0.1`, because that address refers to the ESP32 itself.

Do not place database credentials or backend secrets on the ESP32 or in frontend environment variables. This initial backend stores telemetry in memory, so readings are cleared when the server restarts.
