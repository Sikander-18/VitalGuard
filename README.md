# VitalGuard

**AI-Powered Real-Time Patient Health Monitoring System**

VitalGuard connects to a wearable BLE sensor, analyzes patient vitals using AI, and automatically triggers emergency calls when a critical condition is detected — all through a live dashboard accessible to both patients and doctors.

---

## Key Features

- **Real-Time BLE Vitals** — Captures Heart Rate, SpO2, Blood Pressure, and HRV from a MAX30102 sensor via Bluetooth. Includes a built-in simulation engine with presets (Normal, Tachycardia, Hypoxia, Critical) for demos.
- **AI Classification** — A LangGraph agent powered by Groq (Llama 3.3 70B) classifies vitals as Normal, Future Alert, or Critical in real time, and generates patient-specific recommended actions.
- **Automatic Emergency Calls** — On critical detection, the system calls ALL emergency contacts provided during onboarding using Twilio Voice API with text-to-speech.
- **Live Dashboards** — Patient dashboard shows real-time vitals, AI alerts, charts, and a map. Admin dashboard shows all registered patients, their locations, doctor assignments, and alerts.
- **Role-Based Auth & Onboarding** — Firebase Authentication with Patient and Admin roles. Multi-step onboarding captures medical history, family history, emergency contacts, and geolocation.
- **WebSocket Streaming** — AI-classified vitals are pushed instantly to dashboards via per-user WebSocket connections.

---

## Tech Stack

| Layer    | Technology                                                  |
| -------- | ----------------------------------------------------------- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Leaflet |
| Backend  | FastAPI, SQLAlchemy (async), SQLite                         |
| AI       | LangGraph, Groq API (Llama 3.3 70B)                         |
| Hardware | Smartwatch                                                  |
| Auth     | Firebase Authentication                                     |
| Alerts   | Twilio Voice API                                            |

---

## Project Structure

```
VitalGuard/
├── src/                        # React Frontend
│   ├── components/             # UI Components (VitalCard, MapComponent, etc.)
│   ├── pages/                  # Auth, Onboarding, UserDashboard, AdminDashboard
│   ├── hooks/                  # useVitals (real-time data hook)
│   ├── context/                # AuthContext (Firebase)
│   ├── config/                 # Firebase config
│   └── data/                   # Mock data (fallback)
├── whole_backend/              # FastAPI Backend
│   └── backend/
│       ├── agents/             # LangGraph AI pipeline (nodes, graph)
│       ├── db/                 # SQLAlchemy models & database
│       ├── engine/             # Rule engine for anomaly detection
│       ├── routes/             # REST endpoints (users, vitals, alerts, doctors)
│       ├── services/           # Emergency (Twilio) & WebSocket managers
│       ├── config.py           # Environment config
│       ├── schemas.py          # Pydantic schemas
│       └── main.py             # FastAPI app entry
├── VG_Real_data/               # BLE Hardware Relay
│   ├── app2.py                 # BLE + Simulation relay server (Flask)
│   └── requirements.txt        # Python dependencies
├── PROJECT_DESCRIPTION.txt     # Judge-friendly feature summary
└── README.md                   # This file
```

---

## Setup & Run

### 1. Frontend

```bash
npm install
npm run dev            # Runs on http://localhost:8080
```

### 2. Backend

```bash
cd whole_backend
pip install -r requirements.txt
```

Create `whole_backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
TWILIO_TARGET_PHONE_NUMBER=+91xxxxxxxxxx
```

```bash
python -m uvicorn backend.main:app --port 8000
```

### 3. BLE Relay (Hardware / Simulation)

```bash
cd VG_Real_data
pip install -r requirements.txt
python app2.py         # Runs on http://localhost:5000
```

Toggle simulation mode:

```bash
curl -X POST http://localhost:5000/toggle-simulation -H "Content-Type: application/json" -d '{"preset": "CRITICAL"}'
```

---

## How It Works

1. **Sensor → Relay** — BLE sensor streams vitals to `app2.py` (or simulation generates them).
2. **Relay → Backend** — Relay forwards data to FastAPI every 30 seconds.
3. **Backend → AI** — Rule engine detects anomalies → LangGraph agent classifies severity.
4. **Backend → Alert** — On critical, Twilio calls all emergency contacts.
5. **Backend → Dashboard** — WebSocket pushes classified vitals to the React frontend in real time.
