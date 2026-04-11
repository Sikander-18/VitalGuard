# Product Requirements Document — VitalGuard v2

**Product:** VitalGuard — AI-Powered Clinical Deterioration Detection  
**Version:** 2.0  
**Team:** Code Conquerors  
**Build Type:** National Hackathon  
**Status:** Complete

---

## 1. Product Overview

VitalGuard is an autonomous AI agent that monitors patient vital signs in real time, scores clinical risk using the NHS-validated Modified Early Warning Score (MEWS), and takes real-world action — sending SMS alerts, placing emergency voice calls, and booking doctor appointments — without human intervention.

The system is designed as a full clinical decision pipeline:

```
Sensor → Evidence-based risk scoring → AI reasoning → Autonomous action
```

It is not a passive health dashboard. Every reading triggers a scored risk assessment, an AI reasoning chain, and a conditional action — all within a 1-second loop.

---

## 2. Goals and Non-Goals

**Goals**
- Detect patient deterioration before it becomes critical using predictive trend analysis
- Score risk using a clinically validated, peer-reviewed framework (MEWS)
- Automate emergency response (SMS, voice call, doctor email) with zero human latency
- Provide full explainability of every AI decision for clinical and regulatory trust
- Support multiple patient archetypes with physiologically accurate baselines
- Operate fully offline (air-gapped) using a local LLM fallback

**Non-Goals**
- Replacing a physician's diagnosis
- Ingesting real wearable hardware (v2 uses a clinical-grade simulator)
- Multi-user / multi-tenant hospital deployment
- FDA/CE medical device certification (hackathon scope)

---

## 3. Users

| User | Need |
|---|---|
| Patient | Receive timely alerts when vitals deteriorate |
| Emergency Contact | Be notified immediately in a critical event |
| Doctor | Receive structured appointment requests with full vitals context |
| Hackathon Judge | Inspect every AI decision step and understand clinical accuracy |
| Demo Operator | Switch patient profiles and scenarios in real time |

---

## 4. System Architecture

```
Browser GPS ──┐
              ↓
[WearableSimulator]  ── MIMIC-III distributions ── circadian + noise model
              ↓
[RiskEngine]  ──── MEWS scoring ── trend regression ── LLM validation
              ↓
[LangGraph Agent] ── 4 nodes ── llama3.1:8b (Ollama local fallback)
    ├── vitals_analyzer   (clinical interpretation)
    ├── anomaly_detector  (urgency + trend context)
    ├── decision_maker    (log | alert | doctor | emergency)
    └── action_executor   ── Twilio SMS + Voice + Email
              ↓
[WebSocket] → Live Dashboard → Explainability Trace Panel
```

**Stack:** FastAPI · WebSocket · LangGraph · LangChain · Ollama (llama3.1:8b) · Twilio · SMTP · Vanilla JS

---

## 5. Feature Specifications

---

### 5.1 Clinical-Grade Vital Signs Simulator

**File:** `simulator.py`

The simulator generates physiologically realistic vital sign streams derived from MIMIC-III / PhysioNet statistical distributions. It is not a random number generator — every reading is grounded in real ICU patient data.

#### 5.1.1 MIMIC-III Derived Scenario Distributions

Four clinical scenarios are modelled, each with mean and standard deviation derived from the MIMIC-III database (Johnson et al., 2016):

| Scenario | HR (bpm) | SpO2 (%) | Temp (°C) | HRV (ms) |
|---|---|---|---|---|
| Normal adult at rest | 80 ± 14 | 97.9 ± 1.3 | 36.8 ± 0.5 | 42 ± 12 |
| Early sepsis | 108 ± 16 | 94.2 ± 2.5 | 38.6 ± 0.8 | 16 ± 5 |
| Critical sepsis | 138 ± 18 | 84.5 ± 4.0 | 39.8 ± 1.0 | 6.5 ± 2.5 |
| Acute MI | 115 ± 25 | 91.0 ± 3.5 | 37.2 ± 0.4 | 8 ± 3 |

Readings are sampled from Gaussian distributions with added sensor noise matching real wearable specs (±1–3 bpm HR, ±0.5% SpO2).

#### 5.1.2 Patient Archetypes

Four patient profiles are supported, each with distinct physiological baselines:

| Profile | Label | HR Base | SpO2 Base | HRV Base |
|---|---|---|---|---|
| `healthy_adult` | Healthy Adult (28 F) | 72 bpm | 98.2% | 48 ms |
| `elderly_patient` | Elderly (74 M, HTN) | 78 bpm | 96.5% | 28 ms |
| `cardiac_patient` | Cardiac (61 M, CHF) | 88 bpm | 95.8% | 18 ms |
| `post_op` | Post-Op (45 F, Day 1) | 82 bpm | 97.0% | 22 ms |

Switching profiles resets the simulator state and drift values. The cardiac patient has a lower HRV baseline and higher HR variance, making the system appropriately more sensitive at lower absolute thresholds.

#### 5.1.3 Circadian Rhythm Model

HR and temperature are adjusted by time of day using validated human circadian physiology:
- HR nadir at ~4 AM (−5 bpm), peak at ~3 PM (+5 bpm)
- Temperature nadir at ~4 AM (−0.4°C), peak at ~6 PM (+0.4°C)

Implemented as a sinusoidal offset applied to every reading.

#### 5.1.4 Physiological Coupling

High heart rate suppresses HRV — a validated autonomic stress response. For every bpm above 90, HRV is penalised by 0.3 ms. This means a patient in tachycardia will simultaneously show reduced HRV, compounding the MEWS score.

#### 5.1.5 Smooth Scenario Transitions

When the operator switches scenario modes, vitals do not jump instantly. A linear interpolation (lerp) over 8 steps smooths the transition, simulating realistic physiological change rather than a step function.

#### 5.1.6 Auto Demo Cycle

The `auto` mode cycles through three scenarios automatically:
- Normal for 25 readings
- Mild anomaly for 15 readings
- Critical emergency for 12 readings

This allows unattended demos without manual intervention.

#### 5.1.7 Rolling History Buffer

A `VitalHistory` deque stores the last 60 readings per session. This buffer is passed to the risk engine for trend analysis and predictive alerting. It is per-WebSocket-session, so multiple browser tabs get independent histories.

---

### 5.2 Risk Scoring Engine

**File:** `risk_engine.py`

The risk engine is the clinical brain of VitalGuard. It runs on every reading and produces a structured `RiskAssessment` with a 0–100 score, a risk level, MEWS score, contributing factors, trend summary, and predictive alerts.

#### 5.2.1 MEWS Scoring

The Modified Early Warning Score (Subbe et al., 2001, QJM) is implemented across four vitals:

**Heart Rate bands:**
| Range (bpm) | Points |
|---|---|
| < 40 | 3 |
| 40–49 | 2 |
| 50–99 | 0 |
| 100–109 | 1 |
| 110–129 | 2 |
| ≥ 130 | 3 |

**SpO2 bands:**
| Range (%) | Points |
|---|---|
| < 84 | 3 |
| 84–87 | 2 |
| 88–93 | 1 |
| 94–100 | 0 |

**Temperature bands:**
| Range (°C) | Points |
|---|---|
| < 35.0 | 2 |
| 35.0–35.9 | 1 |
| 36.0–37.9 | 0 |
| 38.0–38.4 | 1 |
| 38.5–39.4 | 2 |
| ≥ 39.5 | 3 |

**HRV bands (autonomic stress proxy):**
| Range (ms) | Points |
|---|---|
| < 8 | 3 |
| 8–14 | 2 |
| 15–19 | 1 |
| ≥ 20 | 0 |

Maximum MEWS score: 12. NHS rapid response team threshold: ≥ 5.

#### 5.2.2 MEWS-to-Risk Score Mapping

MEWS is mapped to a 0–100 risk score:

| MEWS | Base Score |
|---|---|
| 0 | 5 |
| 1 | 18 |
| 2 | 32 |
| 3 | 50 |
| 4 | 65 |
| 5 | 75 |
| 6 | 82 |
| 7 | 88 |
| 8 | 92 |
| > 8 | 95 |

Multiple concurrent abnormalities compound the score: 3+ flags add a 25% multiplier; 2 flags add 12%.

#### 5.2.3 Risk Levels

| Score | Level |
|---|---|
| 0–30 | LOW |
| 31–60 | MODERATE |
| 61–80 | HIGH |
| 81–100 | CRITICAL |

#### 5.2.4 Trend-Adjusted Scoring

Slopes are computed over the last 10 readings using least-squares linear regression (no external dependencies). Significant trends add to the base score:

- HR rising > 1.5 bpm/reading: adds up to +15 points
- SpO2 falling > 0.05%/reading: adds up to +20 points
- Temperature rising > 0.02°C/reading: adds up to +10 points

#### 5.2.5 Predictive Threshold Crossing

For each vital, the engine projects when the current trend will cross a clinical threshold using the regression slope:

```
steps_to_crossing = (threshold - current_value) / slope
```

If the crossing is projected within 60 seconds (SpO2, HR) or 90 seconds (temperature), a `trend_alert` string is generated and surfaced to the dashboard as a yellow predictive banner — before the vital is actually critical.

Thresholds monitored:
- HR → 140 bpm
- SpO2 → 88%
- Temperature → 39.5°C

#### 5.2.6 LLM Validation (Ollama llama3.1:8b)

For readings with a deterministic score ≥ 25, the engine optionally sends the full clinical context to a locally running `llama3.1:8b` model via Ollama. The LLM can adjust the score, level, factors, and summary. The response is parsed as strict JSON. If Ollama is unavailable, the deterministic score is returned unchanged. The `validated_by` field in the response indicates whether the score was LLM-validated or deterministic.

---

### 5.3 LangGraph Agent Pipeline

**File:** `agents.py`

The agent is a 4-node typed state machine built with LangGraph. It runs on every reading after the risk engine and produces a clinical decision with full explainability trace.

#### 5.3.1 Agent State

The shared state passed between nodes:

| Field | Type | Description |
|---|---|---|
| `vitals` | dict | Current vital signs reading |
| `risk` | dict | Full risk assessment output |
| `location` | dict | GPS coordinates (lat/lng) if available |
| `trend_context` | str | Formatted trend slopes and predictive alerts |
| `clinical_analysis` | str | Output of vitals_analyzer node |
| `anomaly_assessment` | str | Output of anomaly_detector node |
| `decided_action` | str | Action chosen by decision_maker |
| `action_reasoning` | str | Reasoning for the chosen action |
| `action_result` | dict | Result of the executed action |
| `explainability_trace` | list | Step-by-step trace of all node outputs |

#### 5.3.2 Node 1 — Vitals Analyzer

Produces a 2–3 sentence clinical interpretation of the current vitals, MEWS score, risk level, and trend context. Uses `llama3.1:8b` if available; falls back to a deterministic formatted string. Output is appended to the explainability trace.

#### 5.3.3 Node 2 — Anomaly Detector

Evaluates whether the clinical picture represents genuine deterioration and how urgent it is. Skipped entirely (via conditional edge) if risk score ≤ 30 — this reduces latency by ~40% for normal readings. Uses LLM if available; falls back to a formatted risk summary.

#### 5.3.4 Node 3 — Decision Maker

Selects one of four actions. Safety-critical decisions are always deterministic — the LLM is only consulted in the moderate zone (31–60):

| Condition | Action | Rule Type |
|---|---|---|
| Score ≤ 30, no trend alert | `log` | Deterministic |
| Score ≥ 81 | `call_emergency` | Deterministic |
| Score ≥ 61 | `schedule_doctor` | Deterministic |
| Score ≥ 50 + trend alert | `alert_user` | Deterministic |
| Score 31–60 | LLM decides | LLM (with fallback) |

Safety override: if MEWS ≥ 3 and the LLM chose `log`, the action is overridden to `alert_user`.

#### 5.3.5 Node 4 — Action Executor

Calls the appropriate action handler from `actions.py`. For `call_emergency`, also calls `notify_contact` to send SMS + voice call to the emergency contact. Appends the action result to the explainability trace and assembles the full log returned to the WebSocket.

#### 5.3.6 Conditional Edge — Skip Anomaly Detector

```
vitals_analyzer → [score ≤ 30] → decision_maker
vitals_analyzer → [score > 30] → anomaly_detector → decision_maker
```

This is the key LangGraph optimisation: healthy readings skip the anomaly detector entirely.

#### 5.3.7 Agent Timeout

The agent has a 25-second timeout enforced by `asyncio.wait_for`. On timeout, a deterministic fallback response is returned with the MEWS-based risk score and a `log` or `alert_user` action depending on the score.

---

### 5.4 Autonomous Action System

**File:** `actions.py`

The action system dispatches real-world notifications. It implements a one-shot incident lock to prevent alert spam.

#### 5.4.1 One-Shot Incident Lock

Each action type has a boolean flag. Once an action fires, it will not fire again until the patient returns to LOW risk for 3 consecutive readings. This means:
- One SMS per incident, not one per second
- One doctor email per incident
- One emergency call per incident

The incident resets automatically when the patient recovers.

#### 5.4.2 Action: `log`

Records the reading internally. No notification sent. Updates the incident state tracker.

#### 5.4.3 Action: `alert_user`

Sends one SMS to the patient's phone number via Twilio. Message includes:
- Risk score
- Current HR, SpO2, temperature
- Top 2 contributing factors
- Google Maps link if GPS coordinates are available

Falls back to a mock console print if Twilio is not configured.

#### 5.4.4 Action: `schedule_doctor`

Sends one email to the doctor's address via SMTP (Gmail SSL). Email includes:
- Full vitals at time of alert
- Risk score and MEWS score
- Clinical reasoning from the agent
- Bulleted list of triggering factors
- Randomly selected doctor name from a pool of 3

Falls back to a mock console print if SMTP is not configured.

#### 5.4.5 Action: `call_emergency`

Generates a unique case ID (e.g. `EMG-482931`) and triggers `notify_contact` immediately after.

#### 5.4.6 Action: `notify_contact`

Sends one SMS + one voice call to the emergency contact via Twilio:

SMS includes patient name, risk score, HR, SpO2, cause, and GPS location link.

Voice call uses Twilio TTS (Alice voice) to read a structured emergency message including patient name, HR, SpO2, and a statement that emergency services have been contacted.

Both are one-shot — if already fired this incident, both are silently skipped.

#### 5.4.7 Mock Mode

All actions have a mock fallback that prints to the console. This allows the system to run and demonstrate the full pipeline without any Twilio or SMTP credentials.

---

### 5.5 FastAPI Server and WebSocket

**File:** `main.py`

#### 5.5.1 WebSocket Endpoint `/ws`

A single persistent WebSocket connection per browser session. The server runs two concurrent async tasks:
- `listen_for_commands`: receives mode/profile/location commands from the browser
- `monitoring_loop`: generates vitals, scores risk, runs the agent, and emits results every 1 second

**Inbound message types:**

| Type | Payload | Effect |
|---|---|---|
| `set_mode` | `mode: normal\|mild_anomaly\|critical_emergency\|auto` | Changes simulator scenario |
| `set_profile` | `profile: healthy_adult\|elderly_patient\|cardiac_patient\|post_op` | Switches patient archetype |
| `location_update` | `location: {lat, lng}` | Updates GPS coordinates for SMS links |

**Outbound message types:**

| Type | Content |
|---|---|
| `vitals` | Raw vital signs reading |
| `risk` | Full risk assessment (score, level, MEWS, factors, trend) |
| `trend` | Trend summary and predictive alert |
| `decision` | Full agent output including clinical analysis and action |
| `action` | Action result (SMS/call/email status) |
| `trace` | 4-step explainability trace |
| `system` | Mode/profile change confirmations |
| `error` | Agent or processing errors |

#### 5.5.2 REST Endpoints

| Endpoint | Method | Response |
|---|---|---|
| `/` | GET | Serves `index.html` |
| `/api/patients` | GET | Returns available patient profiles with labels |
| `/api/twilio-status` | GET | Returns Twilio config status and incident lock state |

#### 5.5.3 Cache Control

All static files are served with `no-store, no-cache` headers to ensure the browser always loads the latest version during development.

---

### 5.6 Live Dashboard

**Files:** `static/index.html`, `static/app.js`, `static/style.css`

#### 5.6.1 Vital Signs Cards

Four cards display HR, SpO2, temperature, and HRV. Each card includes:
- Current value with unit
- Normal range label
- Rolling sparkline chart (Chart.js canvas)
- Colour-coded progress bar (green → yellow → red)
- Trend direction indicator (↑ ↓ →) updated from trend slopes

#### 5.6.2 Risk Gauge

A circular SVG gauge displays the 0–100 risk score with animated fill. The centre shows the numeric score and risk level label. Colour transitions: green (LOW) → yellow (MODERATE) → orange (HIGH) → red (CRITICAL).

#### 5.6.3 MEWS Breakdown Panel

Displays the current MEWS score as `X/12` with a segmented scale bar showing the four clinical zones (0–2, 3–4, 5–6, 7+). A cursor indicator moves along the scale to show the current score position.

#### 5.6.4 Predictive Trend Alert Banner

A yellow banner appears above the vitals grid when a predictive crossing is projected. It shows the specific alert text (e.g. "SpO2 projected critical in ~18s") and a "PREDICTIVE" badge. The banner is hidden when no trend alert is active.

#### 5.6.5 Trend Analysis Panel

Displays per-vital slope values (bpm/reading, %/reading, °C/reading, ms/reading) with a mini spark bar for each. Positive slopes are shown in amber/red; negative SpO2/HRV slopes are shown in red. Includes a data source badge: "MIMIC-III derived · PhysioNet distributions".

#### 5.6.6 Autonomous Actions Panel

Displays a live feed of actions taken by the agent. Each entry shows the action type, timestamp, and result (SMS sent, email sent, call placed, or skipped). Entries are prepended so the most recent action is always at the top.

#### 5.6.7 Agent Reasoning Trace Panel

A collapsible panel showing the 4-step LangGraph trace:
1. Vitals Analyzer — clinical interpretation text
2. Anomaly Detector — urgency assessment (or "Skipped — risk score ≤30")
3. Decision Maker — chosen action and rule that fired it
4. Action Executor — action type and result message

Each step is updated in real time as the agent runs. The panel is collapsed by default and expanded via a toggle button.

#### 5.6.8 Agent Decision Log

A scrollable log of all agent decisions. Each entry shows timestamp, risk level badge, MEWS score, decided action, and the first contributing factor. Entries are prepended; the log is capped to prevent unbounded DOM growth.

#### 5.6.9 Header Status Indicators

- MEWS badge: current score with colour coding
- AI badge: shows "llama3.1" or "deterministic" based on `validated_by` field
- SMS badge: shows Twilio configured/mock status
- Connection status: WebSocket connected/disconnected indicator
- Live clock

#### 5.6.10 Patient and Scenario Controls

- Dropdown to switch patient profile (sends `set_profile` over WebSocket)
- Four scenario buttons: Normal, Mild Anomaly, Critical, Auto Demo (sends `set_mode` over WebSocket)
- Active button is highlighted; mode change is confirmed via a system message

---

### 5.7 Configuration

**File:** `config.py`, `.env`

All credentials and settings are loaded from environment variables. No secrets are hardcoded.

| Variable | Purpose | Default |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio account identifier | — |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | — |
| `TWILIO_PHONE_NUMBER` | Twilio sender number | — |
| `TWILIO_ENABLED` | Enable live Twilio calls | `false` |
| `PATIENT_PHONE` | Patient SMS recipient | — |
| `PATIENT_NAME` | Patient display name | `Patient` |
| `EMERGENCY_CONTACT_PHONE` | Emergency contact number | — |
| `EMERGENCY_CONTACT_NAME` | Emergency contact name | `Emergency Contact` |
| `DOCTOR_EMAIL` | Doctor appointment email | — |
| `EMAIL_ENABLED` | Enable live SMTP email | `false` |
| `SMTP_SERVER` | SMTP host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `465` |
| `SMTP_USERNAME` | SMTP login | — |
| `SMTP_PASSWORD` | SMTP password / app password | — |

When `TWILIO_ENABLED=false` or credentials are missing, all actions fall back to mock mode (console print). The system is fully functional without any credentials.

---

## 6. Data Flow — Single Reading Cycle

```
1. WearableSimulator.generate()
   → Samples from MIMIC-III distribution for active scenario
   → Applies circadian offset, sensor noise, physiological coupling
   → Pushes to VitalHistory rolling buffer
   → Returns VitalSigns dataclass

2. compute_risk(vitals, history)
   → _mews_score(): scores HR, SpO2, temp, HRV against NHS bands
   → Maps MEWS to 0–100 base score
   → Applies multi-flag compounding multiplier
   → Runs trend regression over last 10 readings
   → Applies trend slope penalties to score
   → Runs predict_crossing() for HR/SpO2/temp thresholds
   → (Optional) Sends to llama3.1:8b for validation
   → Returns RiskAssessment

3. run_agent(vitals, risk, location)
   → vitals_analyzer: LLM or deterministic clinical interpretation
   → [conditional] anomaly_detector: urgency assessment if score > 30
   → decision_maker: deterministic rules for LOW/CRITICAL/HIGH; LLM for MODERATE
   → action_executor: fires appropriate action handler
   → Returns full_log with explainability_trace

4. WebSocket emits: vitals → risk → trend → decision → action → trace
```

Total cycle time: ~1 second (deterministic) to ~3–5 seconds (with LLM).

---

## 7. Clinical Validation References

- Subbe CP et al. (2001). *Validation of a modified Early Warning Score in medical admissions*. QJM, 94(10):521–526.
- Johnson AEW et al. (2016). *MIMIC-III, a freely accessible critical care database*. Scientific Data, 3, 160035.
- Royal College of Physicians. (2017). *National Early Warning Score (NEWS) 2*. London: RCP.

---

## 8. Setup

```bash
# 1. Copy and fill environment variables
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Pull local LLM for AI validation
ollama pull llama3.1:8b

# 4. Run
python main.py
# → http://localhost:8000
```

---

## 9. Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | HTTP server and REST API |
| `uvicorn[standard]` | ASGI server |
| `websockets` | WebSocket support |
| `langgraph` | 4-node agent state machine |
| `langchain-core` | LLM message types |
| `langchain-ollama` | Ollama LLM integration |
| `pydantic` | Data validation |
| `twilio` | SMS and voice call dispatch |
| `python-dotenv` | Environment variable loading |

No numpy, no pandas, no ML frameworks. All statistical computation (regression, noise) is implemented in pure Python.

---

## 10. Known Constraints

- The simulator generates synthetic data; it does not connect to real wearable hardware in v2.
- The LLM (llama3.1:8b) requires Ollama running locally on port 11434. If unavailable, all AI features fall back to deterministic MEWS scoring — the system remains fully functional.
- The one-shot incident lock is in-memory and per-process. A server restart resets all incident state.
- GPS location is browser-provided and optional. If not available, SMS messages omit the location link.
- SMTP email uses Gmail SSL (port 465). Other providers require changing `SMTP_SERVER` and `SMTP_PORT`.
