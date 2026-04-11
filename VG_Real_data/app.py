import asyncio
import threading
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from bleak import BleakClient

app = Flask(__name__)
CORS(app)

# 🔹 Watch details
ADDRESS = "A9:4D:A6:00:86:68"
CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9f"

# 🔹 Global state
CURRENT_MODE = "HR"

LATEST_DATA = {
    "HR": 0,
    "SPO2": 0,
    "BP": "0/0"
}


# 🔹 Home route
@app.route("/")
def home():
    return "VitalGuard Backend Running 💀"


# 🔹 Mode change API
@app.route("/set-mode", methods=["POST"])
def set_mode():
    global CURRENT_MODE
    data = request.get_json()

    CURRENT_MODE = data["mode"]
    print(f"\n🔥 Mode changed to: {CURRENT_MODE}")

    return jsonify({"status": "ok", "mode": CURRENT_MODE})


# 🔹 Get data API
@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(LATEST_DATA)


# 🔹 BLE data handler
def handle_data(sender, data):
    global CURRENT_MODE, LATEST_DATA
    data_list = list(data)

    for val in data_list:

        # ❤️ HEART RATE
        if CURRENT_MODE == "HR" and 60 <= val <= 120:
            LATEST_DATA["HR"] = val
            print(f"❤️ HR: {val}")

        # 🫁 SPO2
        elif CURRENT_MODE == "SPO2" and 85 <= val <= 100:
            LATEST_DATA["SPO2"] = val
            print(f"🫁 SpO2: {val}")

        # 🩸 BP (SMART ESTIMATION 💀)
        elif CURRENT_MODE == "BP" and 40 <= val <= 120:

            hr = val

            systolic = int(110 + (hr - 60) * 0.5 + random.randint(-5, 5))
            diastolic = int(70 + (hr - 60) * 0.3 + random.randint(-3, 3))

            bp_value = f"{systolic}/{diastolic}"

            LATEST_DATA["BP"] = bp_value

            print(f"🩸 BP: {bp_value}")


# 🔥 BLE LOOP (AUTO RECONNECT)
async def ble_loop():
    while True:
        try:
            print("\nTrying to connect BLE...")

            async with BleakClient(ADDRESS, timeout=20.0) as client:
                print("BLE Connected 💀")

                await asyncio.sleep(2)

                await client.start_notify(CHAR_UUID, handle_data)

                while True:
                    await asyncio.sleep(1)

        except Exception as e:
            print("⚠️ BLE Error:", e)
            print("Reconnecting in 5 seconds...\n")
            await asyncio.sleep(5)


# 🔹 Background BLE thread
def start_ble():
    asyncio.run(ble_loop())


threading.Thread(target=start_ble, daemon=True).start()


# 🔹 Run server
if __name__ == "__main__":
    app.run(port=5000)