import asyncio
import time
from bleak import BleakClient

ADDRESS = "A9:4D:A6:00:86:68"

TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9f"


start_time = time.time()

def handle(sender, data):
    now = time.time() - start_time
    print(f"[{round(now,2)}s] 📡 {list(data)}")


async def main():
    async with BleakClient(ADDRESS, timeout=30.0) as client:
        print("Connected 💀")

        await client.start_notify(TX_UUID, handle)

        print("\n🚨 READY...")
        print("👉 Step 1: Wait (DON'T TOUCH WATCH)")
        await asyncio.sleep(10)

        print("\n👉 Step 2: NOW START HR ON WATCH FAST!")
        await asyncio.sleep(20)

        print("\n✅ Logging done")


asyncio.run(main())