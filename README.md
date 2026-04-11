# 🛡️ VitalGuard: Predictive Health & Emergency Response

VitalGuard (formerly PulseGuard AI) is a next-generation healthcare platform that bridges the gap between wearable hardware and clinical intervention. It provides real-time vital sign monitoring, AI-driven risk assessment, and automated emergency response.

---

## 🚀 System Architecture

VitalGuard is composed of three primary layers working in sync:

1.  **Frontend Dashboard (React)**: High-performance monitoring interface for patients and medical staff.
2.  **FastAPI Backend**: The "brain" of the system, handling data persistence, Twilio-powered alerts, and Groq-powered AI reasoning.
3.  **Real-time Relay Agent (BLE Agent)**: A specialized Python worker that interfaces with wearable hardware via Bluetooth Low Energy (BLE) and streams data to the core backend.

---

## ✨ Key Features

### 🩺 Advanced Monitoring
- **Live Vitals**: Track Heart Rate, SpO2, Blood Pressure, and HRV in real-time.
- **Dynamic Trend Graphs**: Visual health history using high-performance charting.
- **Hardware Integration**: Direct BLE connection to sensor-equipped wearables.

### 🧠 AI & Automation
- **Groq Health Reasoning**: Uses LLMs (via Groq API) to analyze vital trends and provide actionable health insights.
- **Risk Triage**: Automatic classification of patient status (Normal → Future Alert → Critical).
- **Smart SMS Alerts**: Automated Twilio integration for emergency notifications to doctors and family.

### 🏥 Clinical Workflow
- **Medical Onboarding**: Multi-step patient onboarding capturing medical history, baseline stats, and emergency contacts.
- **Doctor Dashboard**: Admin view for monitoring multiple patients with risk-sorted priority.
- **Care Zone Mapping**: Geo-location tracking of patients and doctors using MapLibre GL.
- **Doctor Assignment**: Seamlessly assign available medical staff to critical cases.

---

## 🛠️ Technology Stack

| Layer | Tech Stack |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Recharts, MapLibre GL |
| **Backend** | FastAPI, SQLAlchemy, SQLite (aiosqlite), Pydantic |
| **AI/LLM** | Groq Cloud, LangChain/LangGraph |
| **Communications** | Twilio API (SMS/Voice) |
| **Hardware Link** | Python, Bleak (BLE), Flask (Relay API) |
| **Auth/Identity** | Firebase Authentication |

---

## 📂 Project Structure

```bash
VitalGuard/
├── src/                # React Frontend
│   ├── components/     # UI Primitives & Health-specific components
│   ├── pages/          # Onboarding, User & Admin Dashboards
│   ├── hooks/          # Custom data-fetching & vital-tracking hooks
│   └── lib/            # Utilities (App logic, map config)
├── whole_backend/      # FastAPI Server
│   ├── backend/        # Multi-agent logic (Groq), Database schemas, Twilio service
│   └── main.py         # Backend entry point
└── VG_Real_data/       # BLE Relay Agent
    ├── app2.py         # Main Flask + Bleak hardware bridge
    └── run.py          # Relay startup script
```

---

## 🚦 Getting Started

### 1. Backend Setup
```bash
cd whole_backend
pip install -r requirements.txt
# Configure your .env with GROQ_API_KEY and TWILIO credentials
uvicorn backend.main:app --port 8000
```

### 2. Frontend Setup
```bash
# Root directory
npm install
npm run dev
```

### 3. Hardware Relay (Optional)
*Requires a compatible BLE device.*
```bash
cd VG_Real_data
pip install -r requirements.txt
python app2.py
```

---

## 📡 API & Data Flow
1. **Wearable** sends raw packets via BLE.
2. **Relay Agent** (`app2.py`) parses packets and calculates metrics (HR, HRV, BP).
3. **Relay Agent** forwards data to **FastAPI** (`/vitals/` endpoint).
4. **FastAPI** stores data, triggers **Groq AI** for risk analysis, and sends **Twilio** alerts if "Critical" risk is detected.
5. **Frontend** polls the FastAPI backend for real-time dashboard updates.

---

## 📜 License
This project is licensed under the MIT License.
