"""Bounded-lifetime Windows TLS keys for the splice transport."""

from __future__ import annotations

import asyncio
import threading
import time

from ..utils.logging import log_buffer
from .live_keys import ConnectionSecrets, find_roblox_pid, scan_connection_candidate

_SLOW_KEY_SCAN_MS = 2000


class _ConnectionKeyState:
    candidate_address: int | None = None
    candidate: ConnectionSecrets | None = None
    excluded_addresses: set[int]
    lock: asyncio.Lock | None = None

    def __init__(self) -> None:
        self.candidate_address = None
        self.candidate = None
        self.excluded_addresses = set()
        self.lock = None

    def ensure_lock(self) -> asyncio.Lock:
        if self.lock is None:
            self.lock = asyncio.Lock()
        return self.lock


class KeyProvider:
    """Provide Roblox TLS secrets using read-only process memory scans."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._scan_slots = asyncio.Semaphore(2)
        self._connections: dict[str, _ConnectionKeyState] = {}

    def _connection_state(self, client_random: str) -> _ConnectionKeyState:
        state = self._connections.get(client_random)
        if state is None:
            state = _ConnectionKeyState()
            self._connections[client_random] = state
        return state

    async def get(self, client_random: str, label: str) -> bytes:
        """Return one secret associated with a TLS client random value."""
        pid = find_roblox_pid()
        if pid is None:
            return b''

        state = self._connection_state(client_random)
        started = time.monotonic()
        async with state.ensure_lock():
            if state.candidate is None:
                async with self._scan_slots:
                    if self._stop.is_set():
                        return b''
                    candidate = await asyncio.to_thread(
                        scan_connection_candidate,
                        pid,
                        stop=self._stop,
                        client_random=client_random,
                        exclude_addresses=state.excluded_addresses,
                    )
                if candidate is None:
                    return b''
                state.candidate_address, state.candidate = candidate

            secret = state.candidate.get(label, b'')
        elapsed_ms = (time.monotonic() - started) * 1000
        if secret and elapsed_ms > _SLOW_KEY_SCAN_MS:
            log_buffer.log(
                'TLS',
                f'Slow TLS key lookup: client=default elapsed_ms={elapsed_ms:.0f} found=True',
            )
        return secret

    async def reject_candidate(self, client_random: str) -> bool:
        """Reject the current candidate and scan for another exact match."""
        pid = find_roblox_pid()
        if pid is None:
            return False

        state = self._connection_state(client_random)
        async with state.ensure_lock():
            if state.candidate_address is None or state.candidate is None:
                return False
            state.excluded_addresses.add(state.candidate_address)
            state.candidate_address = None
            state.candidate = None

            async with self._scan_slots:
                if self._stop.is_set():
                    return False
                candidate = await asyncio.to_thread(
                    scan_connection_candidate,
                    pid,
                    stop=self._stop,
                    client_random=client_random,
                    exclude_addresses=state.excluded_addresses,
                )
            if candidate is None:
                return False
            state.candidate_address, state.candidate = candidate
            return True

    def forget(self, client_random: str) -> None:
        """Drop request-derived state for a completed connection."""
        self._connections.pop(client_random, None)

    def clear(self) -> None:
        """Cancel in-flight scans when the proxy stops."""
        self._stop.set()
        self._connections.clear()
