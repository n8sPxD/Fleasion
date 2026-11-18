"""Bounded-lifetime Windows TLS keys for the splice transport."""

from __future__ import annotations

import asyncio
import threading
import time

from ..utils.logging import log_buffer
from .live_keys import SecretMap, find_roblox_pid, scan


class KeyProvider:
    """Provide Roblox TLS secrets using read-only process memory scans."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._scan_slots = asyncio.Semaphore(2)

    async def get(self, client_random: str, label: str) -> bytes:
        """Return one secret associated with a TLS client random value."""
        pid = find_roblox_pid()
        if pid is None:
            return b''

        started = time.monotonic()
        async with self._scan_slots:
            if self._stop.is_set():
                return b''
            secrets: SecretMap = await asyncio.to_thread(
                scan,
                pid,
                stop=self._stop,
                client_random=client_random,
            )

        secret = secrets.get(client_random, {}).get(label, b'')
        elapsed_ms = (time.monotonic() - started) * 1000
        if secret and elapsed_ms > 2000:
            log_buffer.log(
                'TLS',
                f'Slow TLS key lookup: client=default elapsed_ms={elapsed_ms:.0f} found=True',
            )
        return secret

    def clear(self) -> None:
        """Cancel in-flight scans when the proxy stops."""
        self._stop.set()
