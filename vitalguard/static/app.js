/**
 * VitalGuard v2 — Frontend Application
 * Additions over v1:
 *   - MEWS score display + scale cursor
 *   - Trend analysis panel (slope per vital + sparkbars)
 *   - Predictive alert banner
 *   - Explainability trace panel (4-node LangGraph steps)
 *   - Patient profile selector
 *   - AI validation source badge (llama3.1 / deterministic)
 *   - Trend arrows on vital cards
 */

'use strict';

// ── State ─────────────────────────────────────────────────────────
const state = {
    ws: null,
    connected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 20,
    reconnectDelay: 2000,
    currentMode: 'normal',
    currentProfile: 'healthy_adult',
    logEntries: [],
    actionEntries: [],
    twilioStatus: null,
    location: null,
    lastTrendData: null,
    traceVisible: false,
};

// ── DOM cache ─────────────────────────────────────────────────────
const DOM = {};

function cacheDOM() {
    DOM.connectionStatus = document.getElementById('connection-status');
    DOM.statusDot  = DOM.connectionStatus.querySelector('.status-dot');
    DOM.statusText = DOM.connectionStatus.querySelector('.status-text');
    DOM.headerTime = document.getElementById('header-time');
    DOM.twilioBadge = document.getElementById('twilio-badge');
    DOM.llmLabel    = document.getElementById('llm-label');
    DOM.mewsValue   = document.getElementById('mews-value');
    DOM.mewsScoreBig = document.getElementById('mews-score-big');
    DOM.mewsCursor  = document.getElementById('mews-cursor');
    DOM.validatedBy = document.getElementById('validated-by');
    DOM.trendAlertBanner = document.getElementById('trend-alert-banner');
    DOM.trendAlertText   = document.getElementById('trend-alert-text');
    DOM.gaugeFill  = document.getElementById('gauge-fill');
    DOM.gaugeValue = document.getElementById('gauge-value');
    DOM.gaugeLabel = document.getElementById('gauge-label');
    DOM.riskFactors = document.getElementById('risk-factors');
    DOM.actionsList = document.getElementById('actions-list');
    DOM.decisionLog = document.getElementById('decision-log');
    DOM.logCount    = document.getElementById('log-count');
    DOM.traceSteps  = document.getElementById('trace-steps');
    DOM.traceToggleBtn = document.getElementById('trace-toggle-btn');
    DOM.patientSelector = document.getElementById('patient-selector');
}

// ── Init ──────────────────────────────────────────────────────────
function init() {
    cacheDOM();
    initCharts();
    setupScenarioButtons();
    setupPatientSelector();
    startClock();
    connectWebSocket();
    fetchTwilioStatus();
}

// ── Twilio Status ─────────────────────────────────────────────────
async function fetchTwilioStatus() {
    try {
        const res  = await fetch('/api/twilio-status');
        const data = await res.json();
        state.twilioStatus = data;
        const badge = DOM.twilioBadge;
        const label = badge.querySelector('.twilio-label');
        if (data.enabled && data.configured) {
            badge.className   = 'twilio-badge live';
            label.textContent = 'SMS: Live';
        } else {
            badge.className   = 'twilio-badge mock';
            label.textContent = 'SMS: Mock';
        }
    } catch (e) {
        console.error('[VitalGuard] Twilio status failed:', e);
    }
}

// ── Clock ─────────────────────────────────────────────────────────
function startClock() {
    const update = () => {
        DOM.headerTime.textContent = new Date().toLocaleTimeString('en-IN', {
            hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true,
        });
    };
    update();
    setInterval(update, 1000);
}

// ── Patient Selector ──────────────────────────────────────────────
function setupPatientSelector() {
    DOM.patientSelector.addEventListener('change', (e) => {
        state.currentProfile = e.target.value;
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ type: 'set_profile', profile: e.target.value }));
        }
    });
}

// ── Scenario Buttons ──────────────────────────────────────────────
function setupScenarioButtons() {
    document.querySelectorAll('.scenario-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            state.currentMode = btn.dataset.mode;
            document.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({ type: 'set_mode', mode: btn.dataset.mode }));
            }
        });
    });
}

// ── WebSocket ─────────────────────────────────────────────────────
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    state.ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    state.ws.onopen = () => {
        state.connected = true;
        state.reconnectAttempts = 0;
        updateConnectionStatus(true);
        if (state.location?.lat) sendLocation();
        else requestLocationOnce();
        for (const key of Object.keys(CHART_CONFIG)) fillBuffer(key);
    };

    state.ws.onmessage = (event) => {
        try { handleMessage(JSON.parse(event.data)); }
        catch (e) { console.error('[WS] Parse error:', e); }
    };

    state.ws.onclose = () => {
        state.connected = false;
        updateConnectionStatus(false);
        attemptReconnect();
    };

    state.ws.onerror = (e) => console.error('[WS] Error:', e);
}

function sendLocation() {
    if (state.ws?.readyState === WebSocket.OPEN && state.location?.lat) {
        state.ws.send(JSON.stringify({ type: 'location_update', location: state.location }));
    }
}

function attemptReconnect() {
    if (state.reconnectAttempts < state.maxReconnectAttempts) {
        state.reconnectAttempts++;
        DOM.statusText.textContent = `Reconnecting (${state.reconnectAttempts})...`;
        setTimeout(connectWebSocket, state.reconnectDelay);
    } else {
        DOM.statusText.textContent = 'Connection failed';
    }
}

function updateConnectionStatus(connected) {
    DOM.statusDot.className    = 'status-dot ' + (connected ? 'connected' : 'disconnected');
    DOM.statusText.textContent = connected ? 'Live' : 'Disconnected';
}

// ── Message Handler ───────────────────────────────────────────────
function handleMessage(msg) {
    switch (msg.type) {
        case 'vitals':   updateVitals(msg.data);       break;
        case 'risk':     updateRiskGauge(msg.data);    break;
        case 'trend':    updateTrendPanel(msg.data);   break;
        case 'decision': addDecisionLog(msg.data);     break;
        case 'action':   addActionItem(msg.data);      break;
        case 'trace':    updateTracePanel(msg.data);   break;
        case 'system':   console.log('[System]', msg.message); break;
        case 'error':    console.error('[Agent]', msg.message); break;
    }
}

// ── Charts ────────────────────────────────────────────────────────
const CHART_CONFIG = {
    hr:   { color: '#10b981', fill: 'rgba(16,185,129,0.15)',  range: [40,  180] },
    spo2: { color: '#3b82f6', fill: 'rgba(59,130,246,0.15)',  range: [82,  102] },
    temp: { color: '#f97316', fill: 'rgba(249,115,22,0.15)',  range: [33,  42]  },
    hrv:  { color: '#8b5cf6', fill: 'rgba(139,92,246,0.15)',  range: [0,   100] },
};
const CHART_POINTS  = 60;
const chartBuffers  = {};
const chartCanvases = {};

for (const k of Object.keys(CHART_CONFIG)) chartBuffers[k] = [];

function fillBuffer(key) {
    const cfg = CHART_CONFIG[key];
    const mid = (cfg.range[0] + cfg.range[1]) / 2;
    const noise = (cfg.range[1] - cfg.range[0]) * 0.04;
    chartBuffers[key] = Array.from({length: CHART_POINTS},
        () => mid + (Math.random() - 0.5) * noise);
}

function sizeCanvas(canvas) {
    const dpr  = window.devicePixelRatio || 1;
    const card = canvas.closest('.vital-card') || canvas.parentElement.parentElement;
    const w    = card.clientWidth - 48;
    if (w <= 0) return false;
    const h = 64;
    canvas.width  = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.width  = w + 'px';
    canvas.style.height = h + 'px';
    return true;
}

function initCharts() {
    for (const key of Object.keys(CHART_CONFIG)) {
        const canvas = document.getElementById(`chart-${key}`);
        if (!canvas) continue;
        chartCanvases[key] = canvas;
        fillBuffer(key);
        sizeCanvas(canvas);
    }
    [0, 50, 150, 400, 800].forEach(ms =>
        setTimeout(() => { for (const k of Object.keys(chartCanvases)) sizeCanvas(chartCanvases[k]); }, ms)
    );
    window.addEventListener('resize', () => {
        for (const k of Object.keys(chartCanvases)) sizeCanvas(chartCanvases[k]);
    });
    requestAnimationFrame(chartLoop);
}

function pushChartValue(key, value) {
    const buf = chartBuffers[key];
    if (!buf) return;
    buf.push(value);
    if (buf.length > CHART_POINTS) buf.shift();
}

function drawChart(key) {
    const cfg    = CHART_CONFIG[key];
    const canvas = chartCanvases[key];
    if (!canvas) return;
    const buf = chartBuffers[key];
    if (buf.length < 2) return;
    if (canvas.width <= 1) sizeCanvas(canvas);
    if (canvas.width <= 1) return;

    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    const dpr = window.devicePixelRatio || 1;
    const [yMin, yMax] = cfg.range;
    const padding = (yMax - yMin) * 0.08;
    const lo = yMin - padding, hi = yMax + padding;

    function toY(v) {
        return H - ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * H * 0.9 - H * 0.05;
    }

    ctx.clearRect(0, 0, W, H);
    const stepX  = W / (CHART_POINTS - 1);
    const startX = (CHART_POINTS - buf.length) * stepX;

    ctx.beginPath();
    ctx.moveTo(startX, toY(buf[0]));
    for (let i = 1; i < buf.length; i++) ctx.lineTo(startX + i * stepX, toY(buf[i]));
    ctx.lineTo(startX + (buf.length - 1) * stepX, H);
    ctx.lineTo(startX, H);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, cfg.fill); grad.addColorStop(1, 'transparent');
    ctx.fillStyle = grad; ctx.fill();

    ctx.beginPath();
    ctx.moveTo(startX, toY(buf[0]));
    for (let i = 1; i < buf.length; i++) ctx.lineTo(startX + i * stepX, toY(buf[i]));
    ctx.strokeStyle = cfg.color; ctx.lineWidth = 1.5 * dpr;
    ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.stroke();

    const lx = startX + (buf.length - 1) * stepX;
    const ly = toY(buf[buf.length - 1]);
    ctx.beginPath(); ctx.arc(lx, ly, 3 * dpr, 0, Math.PI * 2);
    ctx.fillStyle = cfg.color; ctx.fill();
}

let chartLastFrame = 0;
function chartLoop(ts) {
    if (ts - chartLastFrame >= 33) {
        for (const key of Object.keys(chartCanvases)) drawChart(key);
        chartLastFrame = ts;
    }
    requestAnimationFrame(chartLoop);
}

// ── Vitals Update ─────────────────────────────────────────────────
const VITAL_CONFIG = {
    heart_rate:  { el: 'val-hr',   bar: 'bar-hr',   card: 'card-hr',   chartKey: 'hr',
                   min: 30, max: 200, normalLow: 60, normalHigh: 100, warnHigh: 120, critHigh: 140, warnLow: 50, critLow: 40 },
    spo2:        { el: 'val-spo2', bar: 'bar-spo2', card: 'card-spo2', chartKey: 'spo2',
                   min: 70, max: 100, normalLow: 95, normalHigh: 100, warnLow: 92, critLow: 88 },
    temperature: { el: 'val-temp', bar: 'bar-temp', card: 'card-temp', chartKey: 'temp',
                   min: 33, max: 42, normalLow: 36.1, normalHigh: 37.2, warnHigh: 38, critHigh: 39.5, warnLow: 35.5, critLow: 34.5 },
    hrv:         { el: 'val-hrv',  bar: 'bar-hrv',  card: 'card-hrv',  chartKey: 'hrv',
                   min: 0, max: 100, normalLow: 20, normalHigh: 70, warnLow: 15, critLow: 10 },
};

function updateVitals(data) {
    for (const [key, config] of Object.entries(VITAL_CONFIG)) {
        const value = data[key];
        if (value == null) continue;

        pushChartValue(config.chartKey, value);

        const el   = document.getElementById(config.el);
        const bar  = document.getElementById(config.bar);
        const card = document.getElementById(config.card);

        el.textContent = (key === 'spo2' || key === 'temperature') ? value.toFixed(1) : Math.round(value);
        el.classList.add('value-flash');
        setTimeout(() => el.classList.remove('value-flash'), 500);

        const pct = Math.max(0, Math.min(100, ((value - config.min) / (config.max - config.min)) * 100));
        bar.style.width = pct + '%';

        let severity = 'normal';
        if (config.critHigh != null && value >= config.critHigh)      severity = 'critical';
        else if (config.critLow != null && value <= config.critLow)   severity = 'critical';
        else if (config.warnHigh != null && value >= config.warnHigh) severity = 'warning';
        else if (config.warnLow != null && value <= config.warnLow)   severity = 'warning';

        card.classList.remove('warning', 'critical');
        if (severity !== 'normal') card.classList.add(severity);

        const barColors = { normal: 'var(--color-low)', warning: 'var(--color-moderate)', critical: 'var(--color-critical)' };
        bar.style.background = barColors[severity];
        el.style.color = severity === 'critical' ? 'var(--color-critical)' : severity === 'warning' ? 'var(--color-moderate)' : 'var(--text-primary)';

        const chartDefaults = { hr: '#10b981', spo2: '#3b82f6', temp: '#f97316', hrv: '#8b5cf6' };
        const chartFillDef  = { hr: 'rgba(16,185,129,0.15)', spo2: 'rgba(59,130,246,0.15)', temp: 'rgba(249,115,22,0.15)', hrv: 'rgba(139,92,246,0.15)' };
        const ck = config.chartKey;
        if (severity === 'critical') {
            CHART_CONFIG[ck].color = '#ef4444'; CHART_CONFIG[ck].fill = 'rgba(239,68,68,0.15)';
        } else if (severity === 'warning') {
            CHART_CONFIG[ck].color = '#f59e0b'; CHART_CONFIG[ck].fill = 'rgba(245,158,11,0.15)';
        } else {
            CHART_CONFIG[ck].color = chartDefaults[ck]; CHART_CONFIG[ck].fill = chartFillDef[ck];
        }
    }
}

// ── Risk Gauge ────────────────────────────────────────────────────
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 85;

function updateRiskGauge(data) {
    const score   = data.score || 0;
    const level   = data.level || 'LOW';
    const factors = data.contributing_factors || [];
    const mews    = data.mews_score;
    const validBy = data.validated_by || 'deterministic';

    const offset = GAUGE_CIRCUMFERENCE - (score / 100) * GAUGE_CIRCUMFERENCE;
    DOM.gaugeFill.style.strokeDashoffset = offset;

    const levelColors = { LOW: 'var(--color-low)', MODERATE: 'var(--color-moderate)', HIGH: 'var(--color-high)', CRITICAL: 'var(--color-critical)' };
    const levelGlows  = { LOW: 'var(--color-low-glow)', MODERATE: 'var(--color-moderate-glow)', HIGH: 'var(--color-high-glow)', CRITICAL: 'var(--color-critical-glow)' };

    DOM.gaugeFill.style.stroke = levelColors[level] || levelColors.LOW;
    DOM.gaugeFill.style.filter = `drop-shadow(0 0 12px ${levelGlows[level] || levelGlows.LOW})`;
    DOM.gaugeValue.textContent = score;
    DOM.gaugeValue.style.color = levelColors[level] || levelColors.LOW;
    DOM.gaugeLabel.textContent = level;

    // MEWS
    if (mews != null) {
        DOM.mewsValue.textContent     = mews;
        DOM.mewsScoreBig.textContent  = `${mews}/12`;
        const mewsPct = Math.min(100, (mews / 12) * 100);
        DOM.mewsCursor.style.left = mewsPct + '%';
        DOM.mewsValue.className = 'mews-value ' + (mews >= 7 ? 'mews-crit' : mews >= 5 ? 'mews-high' : mews >= 3 ? 'mews-mod' : 'mews-low');
    }

    // Validated by badge
    const llmBadge = document.getElementById('llm-badge');
    const llmColors = { 'llama3.1': '#14b8a6', 'deterministic': '#64748b' };
    DOM.llmLabel.textContent = `AI: ${validBy}`;
    llmBadge.querySelector('.llm-dot').style.background = llmColors[validBy] || '#64748b';
    if (DOM.validatedBy) DOM.validatedBy.textContent = `Validated by: ${validBy}`;

    // Risk factors
    if (factors.length === 0) {
        DOM.riskFactors.innerHTML = '<p class="no-factors">All vitals normal</p>';
    } else {
        DOM.riskFactors.innerHTML = factors.map(f =>
            `<div class="factor-item">• ${escapeHtml(f)}</div>`
        ).join('');
    }
}

// ── Trend Panel ───────────────────────────────────────────────────
function updateTrendPanel(data) {
    const summary = data.summary || {};
    const alert   = data.alert;

    // Show/hide predictive alert banner
    if (alert) {
        DOM.trendAlertBanner.classList.remove('hidden');
        DOM.trendAlertText.textContent = alert;
    } else {
        DOM.trendAlertBanner.classList.add('hidden');
    }

    const trendMap = {
        hr:   { slope: summary.hr_slope,   el: 'tslope-hr',   bar: 'tbar-hr',   unit: 'bpm/s',  trendEl: 'trend-hr' },
        spo2: { slope: summary.spo2_slope, el: 'tslope-spo2', bar: 'tbar-spo2', unit: '%/s',    trendEl: 'trend-spo2' },
        temp: { slope: summary.temp_slope, el: 'tslope-temp', bar: 'tbar-temp', unit: '°C/s',   trendEl: 'trend-temp' },
        hrv:  { slope: summary.hrv_slope,  el: 'tslope-hrv',  bar: 'tbar-hrv',  unit: 'ms/s',   trendEl: 'trend-hrv' },
    };

    for (const [key, t] of Object.entries(trendMap)) {
        const slope = t.slope;
        if (slope == null) continue;

        const slopeEl = document.getElementById(t.el);
        const barEl   = document.getElementById(t.bar);
        const trendEl = document.getElementById(t.trendEl);

        if (slopeEl) {
            const sign = slope > 0.001 ? '+' : '';
            slopeEl.textContent = `${sign}${slope.toFixed(3)} ${t.unit}`;
            slopeEl.className = 'trend-slope ' + (
                slope > 0.01 ? 'trend-rising' : slope < -0.01 ? 'trend-falling' : 'trend-stable'
            );
        }

        // Sparkbar: center = stable, red right = rising bad, red left = falling bad
        if (barEl) {
            const pct = Math.min(100, Math.abs(slope) * 300);
            barEl.style.width = pct + '%';
            const isBad = (key === 'hr' || key === 'temp') ? slope > 0 : slope < 0;
            barEl.style.background = pct > 10 ? (isBad ? '#ef4444' : '#f59e0b') : '#10b981';
        }

        // Trend arrow on vital card
        if (trendEl) {
            const arrow = slope > 0.005 ? '↑' : slope < -0.005 ? '↓' : '→';
            const cls   = slope > 0.005 ? 'trend-up' : slope < -0.005 ? 'trend-down' : 'trend-flat';
            trendEl.textContent  = arrow;
            trendEl.className    = `vital-trend-indicator ${cls}`;
        }
    }
}

// ── Explainability Trace ──────────────────────────────────────────
window.toggleTrace = function() {
    state.traceVisible = !state.traceVisible;
    DOM.traceSteps.classList.toggle('hidden', !state.traceVisible);
    DOM.traceToggleBtn.textContent = state.traceVisible ? 'Hide trace ▲' : 'Show trace ▼';
};

function updateTracePanel(traceData) {
    if (!Array.isArray(traceData)) return;
    const nodeMap = {
        'vitals_analyzer': 'trace-out-1',
        'anomaly_detector': 'trace-out-2',
        'decision_maker': 'trace-out-3',
        'action_executor': 'trace-out-4',
    };
    for (const step of traceData) {
        const elId = nodeMap[step.step];
        if (!elId) continue;
        const el = document.getElementById(elId);
        if (!el) continue;
        const output = step.output || step.input_summary || '';
        const rule   = step.rule ? ` <span class="trace-rule">[${step.rule}]</span>` : '';
        el.innerHTML = escapeHtml(output).substring(0, 250) + (output.length > 250 ? '…' : '') + rule;

        // Highlight the step card
        const stepCard = el.closest('.trace-step');
        if (stepCard) {
            stepCard.classList.add('trace-active');
            setTimeout(() => stepCard.classList.remove('trace-active'), 1500);
        }
    }
}

// ── Decision Log ──────────────────────────────────────────────────
function addDecisionLog(data) {
    const placeholder = DOM.decisionLog.querySelector('.log-placeholder');
    if (placeholder) placeholder.remove();

    const level    = (data.risk_level || 'LOW').toLowerCase();
    const action   = data.decided_action || 'log';
    const reasoning = data.action_reasoning || data.clinical_analysis || 'Monitoring vitals...';
    const triggers = data.trigger_vitals || [];
    const mews     = data.mews_score;
    const tAlert   = data.trend_alert;

    const ts = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

    const entry = document.createElement('div');
    entry.className = `log-entry level-${level}`;
    entry.innerHTML = `
        <div class="log-time">${ts}</div>
        <div class="log-body">
            <span class="log-action-badge badge-${action}">${formatAction(action)}</span>
            ${tAlert ? `<div class="log-trend-alert">⚡ ${escapeHtml(tAlert)}</div>` : ''}
            <div class="log-reasoning">${escapeHtml(reasoning)}</div>
            <div class="log-details">
                <b>Risk:</b> ${data.risk_score ?? 0}/100 (${data.risk_level ?? 'LOW'})
                ${mews != null ? ` · <b>MEWS:</b> ${mews}/12` : ''}
                ${triggers.length > 0
                    ? `<br><b>Triggered by:</b> <ul class="trigger-list">${triggers.map(t => `<li>${escapeHtml(t)}</li>`).join('')}</ul>`
                    : ''
                }
            </div>
        </div>`;

    entry.addEventListener('click', () => entry.classList.toggle('expanded'));
    DOM.decisionLog.insertBefore(entry, DOM.decisionLog.firstChild);

    state.logEntries.push(data);
    if (state.logEntries.length > 50) {
        state.logEntries.shift();
        if (DOM.decisionLog.children.length > 50) DOM.decisionLog.removeChild(DOM.decisionLog.lastChild);
    }
    DOM.logCount.textContent = `${state.logEntries.length} entries`;
}

function formatAction(action) {
    return {
        log: '📋 Logged', alert_user: '⚠️ Alert', schedule_doctor: '🩺 Doctor',
        call_emergency: '🚨 Emergency', notify_contact: '📱 Contact',
    }[action] || action;
}

// ── Action Items ──────────────────────────────────────────────────
function addActionItem(data) {
    const placeholder = DOM.actionsList.querySelector('.action-placeholder');
    if (placeholder) placeholder.remove();

    const actionType = data.action_type || 'log';
    if (actionType === 'log') return;

    const time = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const icons   = { alert_user: '⚠️', schedule_doctor: '🩺', call_emergency: '🚨', notify_contact: '📱' };
    const classes = { alert_user: 'warning', schedule_doctor: 'doctor', call_emergency: 'emergency', notify_contact: 'contact' };

    const item = document.createElement('div');
    item.className = `action-item ${classes[actionType] || ''}`;
    item.innerHTML = `
        <span class="action-type-icon">${icons[actionType] || '🤖'}</span>
        <div class="action-content">
            <div class="action-message">${escapeHtml(data.message || 'Action taken')}</div>
            <div class="action-detail">${getActionDetail(data)}</div>
        </div>
        <div class="action-time">${time}</div>`;

    DOM.actionsList.insertBefore(item, DOM.actionsList.firstChild);
    if (data.contact_notification) addActionItem(data.contact_notification);

    state.actionEntries.push(data);
    if (state.actionEntries.length > 20) {
        state.actionEntries.shift();
        if (DOM.actionsList.children.length > 20) DOM.actionsList.removeChild(DOM.actionsList.lastChild);
    }
}

function getActionDetail(data) {
    const d = data.details || {};
    const parts = [];
    if (d.trigger_vitals?.length)   parts.push(`Triggers: ${d.trigger_vitals.join(' | ')}`);
    if (d.case_id)                  parts.push(`Case: ${d.case_id}`);
    if (d.doctor)                   parts.push(d.doctor);
    const sms = d.sms_delivery;
    if (sms?.mode === 'live')  parts.push(`📨 SMS sent (${sms.status})`);
    else if (sms?.mode === 'mock') parts.push('📨 SMS (mock)');
    const voice = d.voice_call;
    if (voice?.mode === 'live')    parts.push('📞 Call placed');
    else if (voice?.mode === 'mock') parts.push('📞 Call (mock)');
    return parts.length > 0 ? escapeHtml(parts.join(' · ')) : '';
}

// ── Utilities ─────────────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ── Location ──────────────────────────────────────────────────────
function onLocationSuccess(pos) {
    state.location = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    sendLocation();
}

function requestLocationOnce() {
    if ('geolocation' in navigator) {
        navigator.geolocation.getCurrentPosition(onLocationSuccess,
            e => console.warn('[Geo]', e.message),
            { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 });
    }
}

function initLocationTracking() {
    if (!('geolocation' in navigator)) return;
    requestLocationOnce();
    navigator.geolocation.watchPosition(
        onLocationSuccess,
        e => console.warn('[Geo watch]', e.message),
        { enableHighAccuracy: true, maximumAge: 10000, timeout: 10000 }
    );
}

// ── Start ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    init();
    initLocationTracking();
});
