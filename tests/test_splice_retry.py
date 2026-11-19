from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from fleasion.proxy.splice import APPLICATION, SpliceConnection
from fleasion.proxy.tls_records import TrafficKeys

if TYPE_CHECKING:
    from fleasion.proxy.splice_keys import KeyProvider


class _FakeWireWriter:
    def __init__(self) -> None:
        self.written: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.written.append(data)

    @staticmethod
    async def drain() -> None:
        return None

    @staticmethod
    def close() -> None:
        return None

    @staticmethod
    def is_closing() -> bool:
        return False

    @staticmethod
    async def wait_closed() -> None:
        return None


class _RetryingKeys:
    def __init__(self, wrong: dict[str, bytes], correct: dict[str, bytes]) -> None:
        self.wrong = wrong
        self.correct = correct
        self.use_correct = False

    async def get(self, _client_random: str, label: str) -> bytes:
        secrets = self.correct if self.use_correct else self.wrong
        return secrets.get(label, b'')

    async def reject_candidate(self, _client_random: str) -> bool:
        if self.use_correct:
            return False
        self.use_correct = True
        return True


def test_tls13_application_record_retries_the_next_key_candidate() -> None:
    cipher = 0x1301
    wrong_secret = b'W' * 32
    correct_secret = b'C' * 32
    wrong = {
        'CLIENT_TRAFFIC_SECRET_0': wrong_secret,
        'CLIENT_HANDSHAKE_TRAFFIC_SECRET': wrong_secret,
    }
    correct = {
        'CLIENT_TRAFFIC_SECRET_0': correct_secret,
        'CLIENT_HANDSHAKE_TRAFFIC_SECRET': correct_secret,
    }
    record = TrafficKeys(correct_secret, cipher).encrypt(b'payload', APPLICATION)
    client_wire = _FakeWireWriter()
    upstream_wire = _FakeWireWriter()

    async def run() -> None:
        connection = SpliceConnection(
            asyncio.StreamReader(),
            cast('asyncio.StreamWriter', client_wire),
            asyncio.StreamReader(),
            cast('asyncio.StreamWriter', upstream_wire),
            keys=cast('KeyProvider', _RetryingKeys(wrong, correct)),
        )
        connection.client_random = 'ab' * 32
        connection.cipher = cipher
        connection.client_finished_relayed = True
        assert await connection._application_record(  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
            connection.client, record
        )
        assert await connection.client.plain.readexactly(7) == b'payload'

    asyncio.run(run())
