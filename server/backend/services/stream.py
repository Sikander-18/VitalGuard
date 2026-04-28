"""
VitalGuard v2 — Async Per-Patient Streaming Queue
Lightweight in-memory streaming. Drop-in replaceable with Redis later.
"""

import asyncio
import logging
from typing import Dict, AsyncIterator

logger = logging.getLogger("vitalguard.stream")


class PatientStream:
    """Per-patient async queue for vitals ingestion."""

    def __init__(self, patient_id: str, maxsize: int = 100):
        self.patient_id = patient_id
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)

    async def publish(self, data: dict):
        """Non-blocking publish. Drops oldest if full."""
        if self.queue.full():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self.queue.put(data)

    async def subscribe(self) -> AsyncIterator[dict]:
        """Async iterator that yields items from the queue."""
        while True:
            item = await self.queue.get()
            yield item


class StreamManager:
    """
    Manages per-patient async queues.
    Supports multiple producers (simulator, BLE) and consumers (WebSocket, DB writer).
    """

    def __init__(self):
        self._streams: Dict[str, PatientStream] = {}

    def get_stream(self, patient_id: str) -> PatientStream:
        """Get or create a stream for a patient."""
        if patient_id not in self._streams:
            self._streams[patient_id] = PatientStream(patient_id)
            logger.info(f"Created stream for patient {patient_id}")
        return self._streams[patient_id]

    async def publish(self, patient_id: str, data: dict):
        """Publish vitals to a patient's stream."""
        stream = self.get_stream(patient_id)
        await stream.publish(data)

    async def subscribe(self, patient_id: str) -> AsyncIterator[dict]:
        """Subscribe to a patient's stream."""
        stream = self.get_stream(patient_id)
        async for item in stream.subscribe():
            yield item

    def remove_stream(self, patient_id: str):
        """Remove a patient's stream."""
        if patient_id in self._streams:
            del self._streams[patient_id]
            logger.info(f"Removed stream for patient {patient_id}")

    @property
    def active_patients(self) -> list:
        return list(self._streams.keys())


# Global instance
stream_manager = StreamManager()
