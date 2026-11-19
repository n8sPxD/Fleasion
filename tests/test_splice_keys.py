from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fleasion.proxy import splice_keys
from fleasion.proxy.splice_keys import KeyProvider

if TYPE_CHECKING:
    import pytest

    from fleasion.proxy.live_keys import ConnectionCandidate

_CLIENT_RANDOM = 'ab' * 32


def test_key_provider_reuses_one_candidate_for_every_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates: list[ConnectionCandidate] = [
        (
            0x1000,
            {'CLIENT_TRAFFIC_SECRET_0': b'client-one', 'SERVER_TRAFFIC_SECRET_0': b'server-one'},
        ),
        (
            0x2000,
            {'CLIENT_TRAFFIC_SECRET_0': b'client-two', 'SERVER_TRAFFIC_SECRET_0': b'server-two'},
        ),
    ]
    scans: list[set[int]] = []

    monkeypatch.setattr(splice_keys, 'find_roblox_pid', lambda: 123)

    def scan(
        _pid: int,
        *,
        stop: object | None,
        client_random: str,
        exclude_addresses: set[int],
    ) -> ConnectionCandidate | None:
        del stop
        assert client_random == _CLIENT_RANDOM
        scans.append(set(exclude_addresses))
        return next(
            (candidate for candidate in candidates if candidate[0] not in exclude_addresses),
            None,
        )

    monkeypatch.setattr(splice_keys, 'scan_connection_candidate', scan)
    provider = KeyProvider()

    async def run() -> None:
        assert await provider.get(_CLIENT_RANDOM, 'CLIENT_TRAFFIC_SECRET_0') == b'client-one'
        assert await provider.get(_CLIENT_RANDOM, 'SERVER_TRAFFIC_SECRET_0') == b'server-one'
        assert await provider.reject_candidate(_CLIENT_RANDOM)
        assert await provider.get(_CLIENT_RANDOM, 'CLIENT_TRAFFIC_SECRET_0') == b'client-two'
        assert await provider.get(_CLIENT_RANDOM, 'SERVER_TRAFFIC_SECRET_0') == b'server-two'
        assert not await provider.reject_candidate(_CLIENT_RANDOM)

    asyncio.run(run())
    assert scans == [set(), {0x1000}, {0x1000, 0x2000}]
