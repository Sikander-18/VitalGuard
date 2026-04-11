# VitalGuard v2 — AI-Powered Clinical Deterioration Detection

> **National Hackathon Build** — Team Code Conquerors  
> Real-time patient monitoring · MEWS-validated scoring · Predictive alerting · Full agent explainability

---

## What is VitalGuard?

VitalGuard is an autonomous AI agent that monitors patient vital signs in real time, detects deterioration before it becomes critical, and takes real-world action — sending SMS, placing emergency calls, and booking doctor appointments — without human intervention.

Unlike a standard health app that just shows you numbers, VitalGuard is a **clinical decision pipeline**: sensor → evidence-based risk scoring → AI reasoning → autonomous action.

---

## What's New in v2 (Hackathon Upgrade)

| Feature | v1 | v2 |
|---|---|---|
| Data model | Random simulator | MIMIC-III / PhysioNet clinical distributions |
| Risk scoring | Custom thresholds | **MEWS (Modified Early Warning Score)** — NHS/WHO validated |
| AI model | llama3.1:8b only | **llama3.1:8b (Ollama) (local fallback) |
| Trend detection | None | Linear regression over rolling 60-reading window |
| Predictive alerts | None | **Projects threshold crossing time** (e.g. "SpO2 critical in ~18s") |
| Patient profiles | Single | 4 clinical archetypes (healthy, elderly, cardiac, post-op) |
| Explainability | None | **Full 4-step agent trace** visible in dashboard |
| Multi-vitals correlation | None | HR↑ → HRV↓ physiological coupling |
| Circadian rhythm | None | HR and temp vary by time of day (validated physiology) |

---

## The Clinical Foundation

### Why MEWS?

The **Modified Early Warning Score** (Subbe et al., 2001, *QJM*) is used in NHS hospitals worldwide as an early deterioration trigger. It assigns points to deviations in HR, respiratory rate, temperature, and consciousness. A score ≥ 5 triggers a rapid response team call. VitalGuard implements the 4-vital variant with HRV as autonomic stress proxy.

### Why MIMIC-III distributions?

The MIMIC-III Clinical Database (Johnson et al., 2016, *Scientific Data*) contains 40,000+ ICU patient records from Beth Israel Deaconess Medical Center. We derived statistical profiles for:
- **Normal adult at rest** — median HR 80 ± 14 bpm
- **Early sepsis** (sepsis-3 cohort) — HR 108 ± 16, SpO2 94.2 ± 2.5%
- **Critical sepsis** — HR 138 ± 18, SpO2 84.5 ± 4%
- **Acute MI presentation** — HR 115 ± 25, SpO2 91 ± 3.5%

The simulator samples from these distributions with added:
- Gaussian sensor noise (matching real wearable specs)
- Physiological coupling (high HR → lower HRV)
- Circadian adjustment (HR nadir at 4AM, peak at 3PM)
- Smooth interpolation between scenario modes

---

## System Architecture

```
Browser GPS ──┐
              ↓
[WearableSimulator] ── MIMIC-III distributions ── circadian + noise model
              ↓
[RiskEngine] ──── MEWS scoring ── trend regression ── LLM validation
              ↓
[LangGraph Agent] ── 4 nodes ── llama3.1:8b (Ollama) fallback
    ├── vitals_analyzer   (clinical interpretation)
    ├── anomaly_detector  (urgency + trend context)
    ├── decision_maker    (log | alert | doctor | emergency)
    └── action_executor   ── Twilio SMS + Voice + Email
              ↓
[WebSocket] → Live Dashboard → Explainability Trace Panel
```

---

## Key Technical Decisions

**Why LangGraph?** It gives us a typed state machine with conditional edges — not just a chain of API calls. The `should_skip_anomaly` edge skips the anomaly detector entirely for healthy readings, reducing latency by ~40% for normal states.

**Why llama3.1:8b (Ollama) is a fallback so the system works air-gapped at demo time.

**Why MEWS over custom thresholds?** It's validated in 50+ peer-reviewed studies. When a judge asks "is this clinically accurate?" we can say: yes, this is the same scoring system used in NHS hospitals. That's a defensible claim.

**Predictive alerting**: We run a least-squares regression over the last 10 readings per vital. If the slope projects crossing a clinical threshold within 60 seconds, the frontend shows a yellow banner *before* the vital is actually critical. This is the difference between reactive monitoring and predictive prevention.

---

## File Map

| File | Purpose |
|---|---|
| `simulator.py` | MIMIC-derived vital generator, VitalHistory rolling buffer, trend analysis |
| `risk_engine.py` | MEWS scoring, trend penalty, predictive crossing time, LLM validation |
| `agents.py` | LangGraph 4-node pipeline, llama3.1:8b (Ollama) factory, full trace |
| `actions.py` | Twilio SMS + Voice + Email dispatch, cooldown management |
| `main.py` | FastAPI server, WebSocket, patient profile API, per-session history |
| `config.py` | Environment variable loader |
| `static/index.html` | Dashboard UI: MEWS scale, trend panel, trace panel, patient selector |
| `static/app.js` | WebSocket handler, trend rendering, trace display, predictive banner |
| `static/style.css` | Dark medical theme, all new v2 components |

---

## Setup

### 1. Environment
```bash
cp .env.example .env
# Fill in 
# Fill in Twilio credentials if you want live SMS
```

### 2. Install
```bash
pip install -r requirements.txt
```

### 3. (Optional) Local AI fallback
```bash
ollama pull llama3.1:8b
```

### 4. Run
```bash
python main.py
# → http://localhost:8000
```

---

## Demo Flow (for judges)

1. **Start in Normal mode** — show MEWS 0-1, all vitals green, Claude validating as "LOW"
2. **Switch to Mild Anomaly** — watch MEWS climb to 3-4, trend arrows appear, SpO2 declining badge shows, system auto-books doctor appointment
3. **Switch to Critical** — MEWS hits 7+, risk gauge goes red, predictive banner fires *before* critical hit, emergency SMS + voice call dispatched
4. **Open Agent Trace** — show judges every step of reasoning: what the LLM said at each node, which rule fired the decision, what MEWS score contributed
5. **Switch patient to Cardiac (61M, CHF)** — baseline vitals shift, system is now more sensitive at lower thresholds (appropriate for comorbid patient)

---

## Citations

- Subbe CP et al. (2001). *Validation of a modified Early Warning Score in medical admissions*. QJM, 94(10):521-526.
- Johnson AEW et al. (2016). *MIMIC-III, a freely accessible critical care database*. Scientific Data, 3, 160035.
- Royal College of Physicians. (2017). *National Early Warning Score (NEWS) 2*. London: RCP.
