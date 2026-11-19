from __future__ import annotations

from typing import TYPE_CHECKING

from fleasion.proxy import live_keys

if TYPE_CHECKING:
    from collections.abc import Iterator

    import pytest


_CLIENT_RANDOM = 'ab' * 32
_SECOND_CANDIDATE = 0x2000


def test_scan_handle_skips_rejected_key_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    excluded = {0x1000}

    def read(_handle: int, address: int, size: int) -> bytes:
        raw = bytearray(size)
        raw[0x18:0x20] = 0x50.to_bytes(8, 'little')
        raw[0x184:0x1A4] = bytes.fromhex(_CLIENT_RANDOM)
        assert address in {0x1000, 0x2000}
        return bytes(raw)

    def validate(raw: bytes) -> tuple[str, dict[str, bytes]]:
        assert len(raw) >= live_keys.STRUCT_SIZE
        return _CLIENT_RANDOM, {'marker': str(int.from_bytes(raw[0x184:0x185], 'big')).encode()}

    monkeypatch.setattr(
        live_keys,
        '_candidates',
        candidates_for_scan,
    )
    monkeypatch.setattr(live_keys, '_read', read)
    monkeypatch.setattr(live_keys, 'validate_openssl_struct', validate)
    monkeypatch.setattr(live_keys, '_remember_candidate_address', remember)
    monkeypatch.setattr(live_keys, '_remember_scan_location', remember)

    secrets, candidate = live_keys._scan_handle(  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
        1,
        2,
        0,
        0x100,
        stop=None,
        wanted=bytes.fromhex(_CLIENT_RANDOM),
        client_random=_CLIENT_RANDOM,
        excluded_addresses=excluded,
    )

    assert candidate is not None
    assert candidate[0] == _SECOND_CANDIDATE
    assert secrets == {_CLIENT_RANDOM: candidate[1]}


def candidates_for_scan(
    *_args: object, **_kwargs: object
) -> Iterator[tuple[int, tuple[int, int], int]]:
    return iter(
        [
            (0x1000, (0, 16), 0),
            (_SECOND_CANDIDATE, (0, 16), 0),
        ]
    )


def remember(*_args: object) -> None:
    return None
