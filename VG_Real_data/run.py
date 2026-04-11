import asyncio
from bleak import BleakClient

ADDRESS = "A9:4D:A6:00:86:68"

RX_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
TX_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"


def handle(sender, data):
    print("🔥 RAW:", list(data))


async def main():
    async with BleakClient(ADDRESS) as client:
        print("Connected 💀")

        await client.start_notify(TX_UUID, handle)

        commands = [
            [0x01],
            [0x02],
            [0x03],
            [0xA0, 0x01],
            [0xAA, 0x01],
            [0x55, 0x01],
        ]

        for cmd in commands:
            print("\nTrying:", cmd)
            await client.write_gatt_char(RX_UUID, bytearray(cmd))
            await asyncio.sleep(6)

asyncio.run(main())