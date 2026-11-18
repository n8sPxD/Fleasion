"""V3 envelopes preserve request metadata and refuse ambiguous conversions."""

# ruff: file-ignore[implicit-namespace-package]

from __future__ import annotations

import json
from typing import cast

import pytest

from fleasion.proxy.asset_batch import (
    decode_v3_request,
    decode_v3_response,
    encode_v3_request,
    encode_v3_response,
)


def _request() -> dict[str, object]:
    return {
        'assets': [
            {
                'requestId': '0',
                'asset': {'assetId': 111, 'access': {'assetVersion': 2}},
                'assetType': 'Mesh',
            },
            {
                'requestId': '1',
                'asset': {'hash': 'abcd1234'},
                'assetType': 'RuntimePropertySet',
            },
        ],
        'batchMetadata': {'nonce': 'keep-me'},
    }


def test_round_trip_with_hashes_and_metadata() -> None:
    original = _request()
    converted = decode_v3_request(json.dumps(original).encode())
    assert converted is not None
    flattened, context = converted
    entries = cast('list[dict[str, object]]', json.loads(flattened))
    assert [entry.get('assetId') for entry in entries] == [111, None]
    rebuilt = encode_v3_request(flattened, context)
    assert rebuilt is not None
    assert json.loads(rebuilt) == original
    entries[0]['assetId'] = 222
    changed = encode_v3_request(json.dumps(entries).encode(), context)
    assert changed is not None
    data = cast('dict[str, object]', json.loads(changed))
    assert data['batchMetadata'] == {'nonce': 'keep-me'}
    remaining = cast('list[dict[str, object]]', data['assets'])
    assert remaining[0]['asset'] == {'assetId': 222, 'access': {'assetVersion': 2}}


def test_response_uses_original_v3_envelope() -> None:
    raw = {'assets': [{'requestId': '0', 'location': 'https://fts.rbxcdn.com/hash'}], 'next': 44}
    converted = decode_v3_response(json.dumps(raw).encode())
    assert converted is not None
    plain, envelope = converted
    entries = cast('list[dict[str, object]]', json.loads(plain))
    entries[0]['location'] = 'https://fts.rbxcdn.com/opaque-route'
    updated = encode_v3_response(json.dumps(entries).encode(), envelope)
    assert updated is not None
    assert json.loads(updated) == {
        'assets': [{'requestId': '0', 'location': 'https://fts.rbxcdn.com/opaque-route'}],
        'next': 44,
    }


@pytest.mark.parametrize(
    'payload',
    [
        b'[]',
        b'not json',
        b'{"assets":{}}',
        b'{"assets":[null]}',
        b'{"assets":[{"requestId":"0","asset":{}} , {"requestId":0,"asset":{}}]}',
        b'{"assets":[{"requestId":"0","asset":42}]}',
    ],
)
def test_malformed_or_ambiguous_request_fails_closed(payload: bytes) -> None:
    assert decode_v3_request(payload) is None


def test_rebuild_rejects_unknown_or_repeated_items() -> None:
    converted = decode_v3_request(json.dumps(_request()).encode())
    assert converted is not None
    _, context = converted
    assert encode_v3_request(b'[{"requestId":"unmatched","assetId":99}]', context) is None
    assert encode_v3_request(b'[{"requestId":"0"},{"requestId":"0"}]', context) is None
