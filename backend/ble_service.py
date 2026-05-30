import asyncio
import logging
from bleak import BleakScanner

logger = logging.getLogger(__name__)

async def scan():
    logger.info("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    for d in devices:
        print(f"Device found: {d.name} [{d.address}]")

if __name__ == "__main__":
    # In a real scenario, this would connect to a specific pulse oximeter
    # or smartwatch, read characteristics, and POST them to the API.
    asyncio.run(scan())
