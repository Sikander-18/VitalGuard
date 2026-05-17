import asyncio
import threading
import random
import uuid
import requests as http_requests
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from bleak import BleakClient, BleakScanner

app = Flask(__name__)
CORS(app)

# 🔹 Watch details
ADDRESS = "A9:4D:A6:00:86:68"
CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9f"
WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9f"

# 🔹 Global state
CURRENT_MODE = "HR"
PENDING_METRIC = None
PENDING_VALUE = None
SIMULATION_MODE = False  # 🔥 Toggle for judge demonstrations
SIM_SCENARIO = "NORMAL" # NORMAL, TACHYCARDIA, HYPOXIA, CRITICAL

FASTAPI_URL = "http://127.0.0.1:8000/vitals/"
USER_ID = "U002"  # Mike Chen

LATEST_DATA = {
    "HR": "--",
    "SPO2": "--",
    "BP": "--/--",
    "HRV": "--"
}

ble_client = None
ble_loop_ref = None # 🔥 Reference to the background asyncio loop

import sys

# ===============================
# FORWARD TO FASTAPI BACKEND
# ===============================
def forward_to_backend():
    """Forward current vitals to the FastAPI backend."""
    try:
        hr = LATEST_DATA.get("HR")
        spo2 = LATEST_DATA.get("SPO2")
        bp = LATEST_DATA.get("BP", "--/--")
        hrv = LATEST_DATA.get("HRV")

        if hr == "--" and spo2 == "--" and bp == "--/--":
            return

        bp_parts = str(bp).split("/")
        systolic = int(bp_parts[0]) if bp_parts[0] != "--" else None
        diastolic = int(bp_parts[1]) if len(bp_parts) > 1 and bp_parts[1] != "--" else None

        payload = {
            "user_id": USER_ID,
            "bpm": hr if isinstance(hr, int) else None,
            "spo2": float(spo2) if isinstance(spo2, (int, float)) else None,
            "systolic": systolic,
            "diastolic": diastolic,
            "hrv": float(hrv) if isinstance(hrv, (int, float)) else None,
            "raw_json": json.dumps(LATEST_DATA, default=str)
        }

        response = http_requests.post(FASTAPI_URL, json=payload, timeout=2)
        print(f"[FORWARD] Sent to FastAPI (Status: {response.status_code}): HR={hr} SpO2={spo2} BP={bp}")
        sys.stdout.flush()
    except Exception as e:
        print(f"[FORWARD] FastAPI unavailable: {e}")
        sys.stdout.flush()

# ===============================
# SIMULATION ENGINE
# ===============================
def simulation_worker():
    """Generates synthetic vitals for judge demos."""
    global LATEST_DATA, SIMULATION_MODE, SIM_SCENARIO
    print("Simulation Worker Started")
    sys.stdout.flush()
    
    while True:
        try:
            if SIMULATION_MODE:
                if SIM_SCENARIO == "NORMAL":
                    LATEST_DATA["HR"] = random.randint(70, 85)
                    LATEST_DATA["SPO2"] = random.randint(97, 99)
                    LATEST_DATA["BP"] = f"{random.randint(115, 125)}/{random.randint(75, 85)}"
                    LATEST_DATA["HRV"] = random.randint(40, 60)
                
                elif SIM_SCENARIO == "TACHYCARDIA":
                    LATEST_DATA["HR"] = random.randint(110, 135) # High
                    LATEST_DATA["SPO2"] = random.randint(95, 98)
                    LATEST_DATA["BP"] = f"{random.randint(130, 145)}/{random.randint(85, 95)}"
                    LATEST_DATA["HRV"] = random.randint(20, 35)
                
                elif SIM_SCENARIO == "HYPOXIA":
                    LATEST_DATA["HR"] = random.randint(90, 105)
                    LATEST_DATA["SPO2"] = random.randint(85, 91) # Low SpO2 !!
                    LATEST_DATA["BP"] = f"{random.randint(100, 115)}/{random.randint(65, 75)}"
                    LATEST_DATA["HRV"] = random.randint(30, 45)

                elif SIM_SCENARIO == "CRITICAL":
                    LATEST_DATA["HR"] = random.randint(140, 160) # Extreme
                    LATEST_DATA["SPO2"] = random.randint(80, 88) # Extreme
                    LATEST_DATA["BP"] = f"{random.randint(160, 180)}/{random.randint(100, 110)}"
                    LATEST_DATA["HRV"] = random.randint(5, 15)

                print(f"[MOCK] Scenario: {SIM_SCENARIO} | Vitals: {LATEST_DATA}")
                sys.stdout.flush()
                forward_to_backend()
                time.sleep(4) # Update every 4 seconds in sim mode
            else:
                time.sleep(1)
        except Exception as e:
            print(f"Simulation Error: {e}")
            sys.stdout.flush()
            time.sleep(1)

# ===============================
# BLE COMMANDS & UTILS
# ===============================
def build_packet(cmd, key, data=b''):
    length = len(data) + 5
    packet = bytearray([0xDF, (length >> 8) & 0xFF, length & 0xFF, 0x00, cmd, 0x01, key, (len(data) >> 8) & 0xFF, len(data) & 0xFF])
    packet.extend(data)
    checksum = sum(b for i, b in enumerate(packet) if i != 3)
    packet[3] = checksum & 0xFF
    return bytes(packet)

async def send_command_async(cmd):
    """Internal async sender."""
    global ble_client
    if ble_client and ble_client.is_connected:
        try:
            await ble_client.write_gatt_char(WRITE_UUID, cmd)
            print(f"[BLE] Sent: {list(cmd)}")
        except Exception as e:
            print(f"[BLE] Write Error: {e}")
    else:
        print("[BLE] Not connected")

def run_cmd_threadsafe(cmd):
    """Safely runs async command from Flask thread."""
    if ble_loop_ref:
        asyncio.run_coroutine_threadsafe(send_command_async(cmd), ble_loop_ref)
    else:
        print("[BLE] Loop not initialized")

# ===============================
# FLASK ROUTES
# ===============================
@app.route("/")
def home():
    return jsonify({"status": "running", "ble_connected": ble_client.is_connected if ble_client else False, "simulation": SIMULATION_MODE})

@app.route("/data")
def get_data():
    return jsonify(LATEST_DATA)

@app.route("/toggle-simulation", methods=["POST"])
def toggle_simulation():
    global SIMULATION_MODE, SIM_SCENARIO
    data = request.get_json() or {}
    SIMULATION_MODE = data.get("enabled", not SIMULATION_MODE)
    if "scenario" in data:
        SIM_SCENARIO = data["scenario"].upper()
    return jsonify({"status": "ok", "simulation_mode": SIMULATION_MODE, "scenario": SIM_SCENARIO})

@app.route("/start-hr", methods=["POST"])
def start_hr():
    run_cmd_threadsafe(build_packet(5, 4, bytes([1])))
    return jsonify({"status": "HR triggered"})

@app.route("/start-spo2", methods=["POST"])
def start_spo2():
    run_cmd_threadsafe(build_packet(5, 14, bytes([1])))
    return jsonify({"status": "SpO2 triggered"})

@app.route("/stop", methods=["POST"])
def stop():
    run_cmd_threadsafe(build_packet(5, 4, bytes([0])))
    return jsonify({"status": "Stopped"})

# ===============================
# BLE CORE
# ===============================
def handle_data(sender, data):
    global LATEST_DATA, PENDING_METRIC, PENDING_VALUE
    packet = list(data)
    if not packet: return

    if packet[0] == 223 and len(packet) >= 7:
        key = packet[6]
        if key == 4: PENDING_METRIC = "HR"
        elif key == 14: PENDING_METRIC = "SPO2"
        elif key == 5:
            PENDING_METRIC = "BP"
            PENDING_VALUE = packet[19] if len(packet) > 19 else None
    elif len(packet) == 1:
        val = packet[0]
        if PENDING_METRIC == "SPO2" and 80 <= val <= 100:
            LATEST_DATA["SPO2"] = val
            forward_to_backend()
        elif PENDING_METRIC == "HR" and 40 <= val <= 200:
            LATEST_DATA["HR"] = val
            LATEST_DATA["HRV"] = max(10, min(140, int(120 - (val * 0.7) + random.randint(-3, 3))))
            forward_to_backend()
        elif PENDING_METRIC == "BP" and PENDING_VALUE:
            LATEST_DATA["BP"] = f"{PENDING_VALUE}/{val}"
            forward_to_backend()
        PENDING_METRIC = None

async def ble_loop():
    global ble_client, ble_loop_ref
    ble_loop_ref = asyncio.get_running_loop()
    
    while True:
        try:
            print(f"Scanning for watch {ADDRESS}...")
            device = await BleakScanner.find_device_by_address(ADDRESS, timeout=10.0)
            
            if not device:
                print("Watch not found in scan. Retrying in 5s...")
                await asyncio.sleep(5)
                continue
                
            print(f"Device found! Attempting BLE Connection to {ADDRESS}...")
            async with BleakClient(device, timeout=15.0) as client:
                ble_client = client
                print("BLE Connected")
                await client.start_notify(CHAR_UUID, handle_data)
                
                # Auth/Verification
                uid = uuid.uuid4().hex[:8].encode()
                packet = bytearray([0xDF, 0x00, len(uid) + 5, 0xF1, 0x01, 0x00, 0x00, len(uid)])
                packet.extend(uid)
                await send_command_async(bytes(packet))
                
                while client.is_connected:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"BLE Error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # Start BLE in background thread
    threading.Thread(target=lambda: asyncio.run(ble_loop()), daemon=True).start()
    # Start Simulation in background thread
    threading.Thread(target=simulation_worker, daemon=True).start()
    # Start Flask
    app.run(port=5000, host="0.0.0.0", debug=False)

