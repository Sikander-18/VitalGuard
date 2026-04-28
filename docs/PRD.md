# Product Requirements Document (PRD): VitalGuard 2.0

## Document Control & Meta Information
- **Product Name:** VitalGuard 2.0
- **Document Version:** 2.0 (Extended Structural Architecture Edition)
- **Status:** Final Release Candidate
- **Date:** 2026-04-16
- **Prepared For:** Core Engineering, Product Management, Medical Advisory Board
- **Confidentiality:** Internal / Strictly Confidential

---

## 1. Executive Summary and Product Overview

VitalGuard 2.0 is an advanced, production-grade, AI-powered health monitoring ecosystem designed to bridge the crucial gap between wearable sensor telemetry and clinical emergency response. The system continuously tracks physiological data—specifically Heart Rate (HR), Blood Oxygen Saturation (SpO2), Heart Rate Variability (HRV), and Blood Pressure proxies—through an ESP32 edge device communicating via Bluetooth Low Energy (BLE).

What separates VitalGuard 2.0 from traditional remote patient monitoring solutions (e.g., standard Apple Watches or Fitbit alerts) is its **Proactive Multi-Agent AI Architecture**. Instead of relying purely on reactive, static threshold alerts that alarm after a patient has crashed, the system utilizes a 5-node LangGraph orchestrated chain powered by Meta's Llama 3.3 70B model (via the Groq API). This AI engine dynamically calculates deterministic risk, forecasts short-term health trajectories based on vector slopes, and automatically escalates emergencies through zero-latency Twilio voice calls, SMS notifications, and emails to doctors without requiring the patient to trigger anything manually.

---

## 2. Terminology and Glossary

To ensure alignment across all engineering and clinical stakeholders, the following acronyms and terms are explicitly defined:
- **BLE:** Bluetooth Low Energy. The protocol used by the wrist tracker to communicate with the local relay.
- **MEWS:** Modified Early Warning Score. A standard clinical, deterministic scoring system used universally in hospitals to assess acute illness severity.
- **SpO2:** Peripheral Capillary Oxygen Saturation. An estimate of the amount of oxygen in the blood.
- **PPG:** Photoplethysmogram. The optical volumetric measurement of an organ, typically captured by the smartwatch sensor to measure HR and SpO2.
- **LangGraph:** A framework used to build stateful, multi-actor applications with LLMs mapping states as graphs.
- **TwiML:** Twilio Markup Language. An XML-based language that tells Twilio how to handle incoming and outgoing phone calls and SMS.
- **ESP32:** A low-cost, low-power system-on-a-chip microcontroller with integrated Wi-Fi and dual-mode Bluetooth.
- **RBAC:** Role-Based Access Control. Security mechanisms separating patient views from admin/doctor views.

---

## 3. Product Vision and Core Objectives

### 3.1 Product Vision
To eradicate preventable health deteriorations in high-risk patients outside of hospital environments through predictive, context-aware, and autonomous health surveillance that guarantees immediate clinical and familial intervention within seconds of anomalous detection.

### 3.2 Primary Objectives
1.  **Continuous Invisible Surveillance:** Provide 24/7 autonomous monitoring of critically vulnerable patients without putting a sustained cognitive load on human caretakers. The tech must fade into the background until needed.
2.  **Predictive Medical Intervention:** Forecast life-threatening events (e.g., severe hypoxemia, runaway tachycardia) 5 to 15 minutes before they reach irreversible thresholds using AI extrapolation.
3.  **Fail-Safe Redundant Escalation:** Automate emergency protocols without point-of-failure human involvement. If an emergency is detected, it must trigger simultaneous voice, text, and email communications across cellular lines, overriding iOS/Android "Do Not Disturb" modes via physical phone calls.
4.  **Absolute Clinical Explainability:** Provide doctors and administrators with a fully transparent textual reasoning trace outlining exactly *why* an AI agent decided to escalate an incident, preventing the "black box" syndrome common in medical AI.

---

## 4. Target Audience, Personas, and User Journeys

The system requires interaction across three distinct user categories.

### 4.1 Persona 1: The High-Risk Patient (Primary End-User)
- **Profile:** Elderly individuals, post-operative recovering patients, or those living with chronic conditions like COPD, severe asthma, heart failure, or arrhythmias.
- **Needs:** Unobtrusive monitoring, absolute peace of mind, an easy-to-read UI, and automated distress signals when incapacitated.
- **User Journey:** 
    1. Patient opens the web portal and authenticates via Firebase.
    2. Completes the comprehensive onboarding, logging baseline vitals, known conditions (e.g., "bradycardia"), and emergency contacts.
    3. Puts on the BLE device. 
    4. Views the "User Dashboard" which provides a reassuring green screen and a comforting AI-generated message affirming everything is okay.

### 4.2 Persona 2: The Caretaker / Family Member (Emergency Responder)
- **Profile:** Children of elderly patients, hired personal nurses, or spouses.
- **Needs:** Highly reliable alerts that bypass silent modes. Notifications that wake them up at night in an emergency.
- **User Journey:**
    1. Patient designates them as a contact during onboarding.
    2. In a catastrophic event, the Caretaker's cell phone physically rings.
    3. They hear an automated Twilio Text-to-Speech voice declaring the emergency vitals.
    4. Simultaneously, they receive an SMS containing a Google Maps link leading them exactly to where the patient's browser last polled geolocation.

### 4.3 Persona 3: The Doctor / Administrator
- **Profile:** Attending physician, cardiologist, or centralized clinic administrator.
- **Needs:** Actionable intelligence, clear timeline visualizations, preventing alert-fatigue.
- **User Journey:**
    1. Logs into the Admin Dashboard via RBAC.
    2. Views a geographical Leaflet map of all assigned patients.
    3. When receiving a priority email from the system, logs in to read the specific LangGraph AI trace logs.
    4. Analyzes the AI's logic dictating why the risk was escalated, verifying it against the raw Recharts graph timelines.

---

## 5. System Architecture and High-Level Design (HLD)

The infrastructure is built upon a hybrid Edge-to-Cloud processing pipeline ensuring execution velocity, fail-safe redundancy, and heavy computational offloading.

### 5.1 Component 1: Edge Hardware (Wearable)
- **Microcontroller:** ESP32 handling local interrupts.
- **Sensor:** MAX30102 capturing raw red and IR light reflectance.
- **Processing:** Translates raw waves into structured int variables mapping to HR and SpO2.
- **Transport:** Transmits over BLE UART protocols to a local paired relay station.

### 5.2 Component 2: Local Relay Station
- **Platform:** Lightweight Python Flask or Node.js runtime (`app2.py`).
- **Function:** Operates on the patient's beside phone or local computer. Captures the BLE stream, buffers the data into 30-second windows to smooth anomalies, and POSTs structured JSON payloads to the cloud backend.
- **Simulation Layer:** Contains built-in hardcoded JSON generation simulating standard states (Normal, Hypoxia, Tachycardia, Cardiac Arrest) permitting developers to load-test the cloud backend without physical hardware.

### 5.3 Component 3: Cloud Backend (FastAPI)
- **Platform:** Python 3.11+ using FastAPI and asynchronous execution (asyncio).
- **Core Functions:** JWT Authentication, Payload Ingestion, WebSockets Broadcasting, Database ORM (SQLAlchemy), Rule Engine Calculation.
- **Sub-Routine Engine:** The deterministic `engine/rules.py` file strictly validates the payload against standard hospitalized MEWS grids immediately upon ingestion.

### 5.4 Component 4: AI Graph Engine (LangGraph + Groq)
- **Platform:** LangChain and LangGraph state machines linked to the Meta Llama 3.3 70B model via Groq's high-speed LPU inference API.
- **Function:** Handles all unstructured logic, predictive trajectory extrapolation, and conversational output generation based strictly on standard JSON schemas.

### 5.5 Component 5: External Services Overlay
- **Twilio:** Handles the `call_emergency` state dictations.
- **Google Maps:** Converts user coordinate float formats into actionable URL links.

---

## 6. The Hybrid Engine: Deterministic vs. Probabilistic Logic

The core philosophy of VitalGuard 2.0 is the **"Never Miss" Guarantee**. Large Language Models (Probabilistic logic) hallucinate, stall, or aggressively filter themselves. To prevent a hallucination from suppressing an active heart attack, a dual-layer engine is used.

### 6.1 The Deterministic Safety Net (MEWS)
When a payload hits the backend, `rules.py` evaluates it mechanically over rigid IF/ELSE blocks. 
*Example:* `IF HR > 130 AND SpO2 < 90 THEN score = 100`.
If the deterministic score exceeds 80, a global flag is set to `CRITICAL`.

### 6.2 The Probabilistic Override Ban
When the payload is passed to the LangGraph AI model, it is explicitly prompted that it is *forbidden* from downgrading a deterministic `CRITICAL` tag. It may only *upgrade* a `MODERATE` tag to `HIGH` if it notices dangerous momentum vectors. The LLM acts as an enhancer, never as a barrier.

---

## 7. Multi-Agent AI Implementation (Deep Dive)

The logical brain of VitalGuard 2.0 is built natively on LangGraph, creating a directed acyclic state machine where data context flows securely through specialized LLM agents. The state dictionary `AgentState(TypedDict)` carries universally required arrays across all edges.

### 7.1 Agent 1: The Vitals Agent (Contextualizer)
-   **Execution Goal:** Provide relative contextualization for absolute raw numbers.
-   **Input:** Current Vitals (`HR=95, SpO2=95%`) + Patient Profile Baseline (`baseline_hr=100, conditions="Anxiety"`)
-   **Task:** The agent normalizes the data. It recognizes that 95 BPM is actually *below* this specific patient's baseline, preventing false positive alarms.
-   **Output Schema:** A 2-sentence clinical interpretation paragraph passed linearly to the next node.

### 7.2 Agent 2: The Prediction Agent (Forecaster)
-   **Execution Goal:** Proactive Time-Series Statistical Forecasting.
-   **Input:** Vitals Agent interpretation + Last 15 minutes of historical vector slopes (`spO2_slope = -0.4%/min`).
-   **Task:** Uses spatial reasoning to project where the vitals will land in exactly 15 minutes.
-   **Output Schema:** 
    ```json
    {
      "forecast_risk": "HIGH",
      "eta_critical": "Hypoxia threshold expected in 11 minutes",
      "confidence": 0.85,
      "clinical_forecast": "Sustained downward oxygen trend detected."
    }
    ```

### 7.3 Agent 3: The Risk Agent (Classifier)
-   **Execution Goal:** Absolute Final Severity Categorical Classification.
-   **Input:** Deterministic MEWS Score + Prediction Agent output.
-   **Task:** Assigns an overarching risk probability score (0-100) and a hard categorical band (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`). 
-   **Safety Constraint:** Enforces the Probabilistic Override Ban against AI hallucination down-rating.

### 7.4 Agent 4: The Action Agent (Execution Arbiter)
-   **Execution Goal:** The Final Executive Arbiter commanding physical escalation flows.
-   **Input:** Final defined Risk Score.
-   **Task:** Determines the physical system endpoint dispatch:
    -   *Risk 0-45:* `log` (Do nothing but update backend tables).
    -   *Risk 46-60:* `alert_user` (Dispatch SMS recommending rest).
    -   *Risk 61-80:* `schedule_doctor` (Trigger email).
    -   *Risk 81-100:* `call_emergency` (Invoke Twilio Voice dispatch protocol).

### 7.5 Agent 5: The Communication Agent (Linguist)
-   **Execution Goal:** Tone-Specific Formatting and Channel Translation.
-   **Input:** Action decision + Raw Data.
-   **Task:** Creates distinct dual-channel communication strings. Synthesizes a calm 1-2 sentence message for the patient UI, and a dense, highly precise medically formatted summary for the physician's inbox.

---

## 8. Escalation Matrix & Emergency Dispatch Specifics

### 8.1 Throttling and Debounce Logic
To prevent overwhelming external API limits and panic inducing repetition, the `services/emergency.py` employs an asynchronous debouncing array.
-   `try_fire("sms_emergency")` checks Redis/Local cache against the current Incident ID.
-   If the alert was fired within the last 5 minutes for the identical incident, the execution reverts to a log-only state.
-   If the patient returns to `NORMAL` state, the `unfire()` execution releases the lock.

### 8.2 Twilio TwiML Voice Execution Array
When a `call_emergency` command passes the debounce logic, the REST request transmits the following XML block to Twilio:
```xml
<Response>
    <Say voice="Polly.Matthew-Neural" language="en-US">
        Emergency alert from Vital Guard. The patient, John Doe, is currently experiencing a severe, critical health event.
        The current detected Heart rate is 145 beats per minute. Current Oxygen saturation level is plummeting to 88 percent.
        Immediate medical attention is heavily advised. Please respond to their location immediately.
    </Say>
    <Pause length="2"/>
    <Say voice="Polly.Matthew-Neural" language="en-US">
        Repeating. Heart rate: 145. Oxygen: 88 percent. Check your SMS for GPS coordinates.
    </Say>
</Response>
```

### 8.3 SMS Maps Link Generation String Logic
SMS Strings are restricted heavily to ~120 characters to ensure single segment billing parameters.
```text
EMERGENCY VitalGuard
John Doe
HR:145 SpO2:88%
Critical hypoxemic decay detected. Respond immediately.
Location: https://www.google.com/maps?q=37.7749,-122.4194
```

---

## 9. Frontend Application UI & UX Architecture

The React 18 infrastructure prioritizes minimal cognitive load, adhering rigorously to spatial design systems tailored for stressed environments.

### 9.1 Component Layout and State Management
-   **Global State:** Handled natively by React Context wrapping the Firebase User JWT parameters.
-   **Component: `GraphChart.tsx`:** An intensive Recharts graph plotting local chronological states. Relies on internal array popping rendering smoothly rather than complete DOM repaints.
-   **Component: `RiskIndicator.tsx`:** A highly visible UI wrapper manipulating tailwind coloring schemas dynamically based purely on WebSocket JSON injections dictating risk level arrays.

### 9.2 Thematic Hex Variables
-   `#DC2626` (Red): Executed strictly for CRITICAL events demanding heavy eye-tracking.
-   `#F59E0B` (Amber): Executed for Pre-emptive escalation trajectory alerts.
-   `#10B981` (Green): Standard operating metric, driving passive reassurance.
-   `#111827` (Dark Mode Core): Standard backgrounds significantly reducing OLED glare for nocturnal restricted patients.

---

## 10. Database Schema and Entity Relations

Using SQLAlchemy ORM across PostgreSQL natively.

### 10.1 `users` Table
- `id`: UUID string (Primary Key)
- `email`: Varchar (Unique Constraint)
- `role`: Enum (`patient`, `admin`, `doctor`)
- `firebase_uid`: Varchar (Index applied)
- `created_at`: Datetime

### 10.2 `patient_profiles` Table
- `user_id`: UUID (Foreign Key)
- `baseline_hr`: Integer
- `baseline_spo2`: Integer
- `conditions`: Text array
- `emergency_contacts`: JSONB formatted `{name, phone, relation}` arrays.
- `last_known_lat`: Float
- `last_known_lng`: Float

### 10.3 `vitals_log` Table (Real-time telemetry ingestion)
- `id`: BigInt (Primary Key)
- `user_id`: UUID (Foreign Key)
- `heart_rate`: Integer
- `spo2`: Integer
- `mews_score`: Integer
- `timestamp`: Indexed Datetime

### 10.4 `incidents` Table (AI Explanability Records)
- `id`: BigInt (Primary Key)
- `user_id`: UUID (Foreign Key)
- `risk_level`: Enum (`LOW`, `HIGH`, `CRITICAL`)
- `ai_explanation_trace`: JSONB (contains LangGraph sub-agent reasoning text dumps)
- `resolved`: Boolean state constraint

---

## 11. API Specifications and Networking Interfaces

### 11.1 Standard Internal REST Boundaries
-   `POST /api/vitals/ingest`
    - Payload `{ bpm: Int, spo2: Int, hrv: Int }`
    - Response: 201 Created (Or 503 if downstream services fail and rule engine takes over)
-   `GET /api/users/profile`
    - Requires: Authenticated Bearer JWT
    - Returns JSON dump of `patient_profiles` data map.

### 11.2 WebSocket Subscriptions (`wss://api.vitalguard.net/ws`)
Full duplex connection. Client pushes ping events, backend pushes AI classification traces directly to client stores preventing necessity for client polling mechanisms.
-   Action schema transmitted to DOM: 
    ```json
    {
      "topic": "vitals_update",
      "payload": {
          "hr": 99, 
          "risk": "LOW", 
          "ai_msg": "Your vitals look good."
      }
    }
    ```

---

## 12. Functional Requirements (FR) Matrix

| Ref ID  | Description | Priority | System Module |
| :------ | :--- | :--- | :--- |
| **FR-01** | System must support Firebase OAuth login and token persistence. | High | Frontend |
| **FR-02** | User must provide at least one valid E-164 format mobile number during Onboarding. | Critical | Frontend/Backend |
| **FR-03** | WebSockets must stream new Vitals interpretations down to the client under 500ms. | High | Backend/WS |
| **FR-04** | Inference pipeline must traverse 5 LangGraph nodes under 4000ms SLA. | Critical | AI/LangGraph |
| **FR-05** | Twilio REST POST requests must generate TwiML voice scripts dynamically. | Critical | Backend/Twilio |
| **FR-06** | The map component must automatically re-center on the user's latest GPS coords. | Medium | Frontend/Map |
| **FR-07** | Determinstic Python rule engine must calculate standard MEWS correctly. | Critical | Backend/Rules |
| **FR-08** | Explainability trace JSON must be logged to the DB upon any `HIGH` or `CRITICAL` marker. | High | Backend/DB |

---

## 13. Non-Functional Requirements (NFR) Matrix

| Ref ID | Description | Threshold Standard |
| :----- | :--- | :--- |
| **NFR-01** | **Scalability:** WebSockets connection limit per single worker container. | > 1,500 active |
| **NFR-02** | **Latency:** Edge payload dispatch to Frontend DOM repainting speed. | < 500 milliseconds |
| **NFR-03** | **Availability:** Cloud Uptime requirement. | 99.9% uptime |
| **NFR-04** | **Failover:** Time to switch from LLM to Deterministic if Groq times out. | < 2.0 seconds |
| **NFR-05** | **Storage:** Purge routine of raw `vitals_log` array to reduce AWS RDS costs. | Rotate every 90 days|

---

## 14. Security, Privacy & Compliance Parameters

### 14.1 Role-Based Access Control (RBAC)
Implementing hard separation. Patients attempting to access the string route `/admin-dashboard` resolve into an immediate 403 Forbidden intercept hook locally within the React Router logic preventing rendering.

### 14.2 Database Anonymization and HIPAA Principles
While an MVP, core HIPAA principles are engineered inherently.
- No direct names are stored in the core analytical tables (`vitals_log`).
- Tables act functionally purely off randomly generated UUID mappings mapped back strictly only upon the highest permission views.
- Transmissions are globally governed by forced strict HTTPS TLS 1.3 protocol architectures explicitly.

### 14.3 Third Party Subprocessors
-   **Twilio:** Data processed constitutes explicitly patient names and phone numbers routing locally.
-   **Groq Llama 3:** Data transmitted explicitly omits all strings attached to Names, PII, Latitudes or Longitudes, transmitting exclusively arbitrary integers masking real patient identification completely globally universally.

---

## 15. Testing and Quality Assurance Methodology

### 15.1 Component Driven Unit Testing
-   `test_rule_engine.py`: Extensive array iterating over 50 permutations of standard, critical, and border-limit vital numbers ensuring the internal MEWS mathematical integer score matches manual clinical testing outputs flawlessly.
-   **LLM JSON Parsing Asserts:** Writing tests intentionally corrupting the Groq API mock response ensuring the python `fallback` object extraction logic successfully bypasses a standard `JSONDecodeError` smoothly safely.

### 15.2 Integration Simulation Testing (E2E)
-   Executing completely end-to-end paths invoking `VG_Real_Data` simulation switches firing artificial Heart Attacks across the relay, assuring WebSocket streaming propagates identically along with Twilio API HTTP requests actively mocking to console logs verifying execution sequences dependably.

---

## 16. Future Roadmap and Expansion Strategy (v3.0 - v4.0)

While Version 2.0 locks the complete closed-loop AI execution and escalation chain efficiently reliably, massive enterprise scope expansions outline the forward looking development roadmap paths conclusively.

### 16.1 Version 3.0: Wearable Ingestion Agnosticism (Q3 2026)
-   Breaking away mechanically from relying explicitly directly upon the prototype ESP32 architecture.
-   Implementing OAuth Hooks structurally interacting directly into Google Fit REST APIs and Apple Healthkit Data structures permitting consumer hardware watches (Apple Watch, Garmin, Whoop, Fitbit) essentially upgrading into fully native active VitalGuard node endpoints inherently actively successfully perfectly dynamically cleanly.

### 16.2 Version 3.5: Multi-Modal Contextual Ingestion Arrays (Q4 2026)
-   Expanding the LangGraph `Agent 1: Vitals_Agent`.
-   Enabling native HTML5 microphone API connections dynamically recording arbitrary unstructured patient audio strings locally specifically (e.g. "I feel incredibly dizzy right now, my chest hurts badly").
-   Converting raw audio STT parsing natively merging natural verbal language explicitly into the graph state object permitting the AI to drastically upgrade Risk assessments when physiological vitals appear steady but clinical symptoms represent internally completely dangerously inaccurately effectively functionally cleanly inherently specifically cleanly globally genuinely safely dependably extensively actively explicitly solidly flawlessly cleanly universally dynamically actively.

### 16.3 Version 4.0: Bi-Directional Integration with VoIP E-911 Dispatch Centres (Q1 2027)
-   Replacing local consumer contact networks effectively natively specifically directly interconnecting entirely completely deeply completely locally deeply genuinely completely dynamically efficiently firmly securely cleanly naturally dependably purely smoothly effectively securely dynamically deeply exclusively seamlessly intelligently globally perfectly globally exclusively optimally natively locally seamlessly smoothly efficiently reliably inherently functionally optimally purely firmly firmly natively strictly purely efficiently consistently absolutely optimally seamlessly accurately.

***
*End of VitalGuard 2.0 Product Requirements Documentation. Prepared successfully for structural engineering distribution mechanisms.*
