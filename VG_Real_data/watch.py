import asyncio
from bleak import BleakClient

ADDRESS = "A9:4D:A6:00:86:68"
CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9f"

def handle_data(sender, data):
    print("RAW DATA:", list(data))

async def main():
    async with BleakClient(ADDRESS) as client:
        print("Connected 💀")

        await client.start_notify(CHAR_UUID, handle_data)

        while True:
            await asyncio.sleep(1)

asyncio.run(main())