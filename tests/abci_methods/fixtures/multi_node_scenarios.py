"""Scenarios exercised by the multi-node ABCI tests.

This module centralizes the block flows that are executed across multiple
application instances.  Keeping the transaction definitions in a single place
makes it trivial to expand coverage whenever a new contracting module is
introduced: simply add an additional probe definition in ``MODULE_PROBES`` or
record a new block in ``build_currency_blocks``.
"""

from __future__ import annotations
import binascii
import json
from typing import Dict, Iterable, List, Sequence

from cometbft.abci.v1beta3.types_pb2 import Request, RequestFinalizeBlock
from google.protobuf.timestamp_pb2 import Timestamp

CHAIN_ID = "unique-chain-id-goes-here"
DEFAULT_SIGNATURE = "multi-node-test"

# Accounts whose balances are explicitly seeded before scenarios execute.  The
# values are kept intentionally small so the resulting state changes are easy to
# reason about in assertions and when debugging.
SCENARIO_ACCOUNT_BALANCES: Dict[str, int] = {
    "sys": 10_000_000,
    "multi_node_operator": 5_000_000,
    "module_probe_receiver": 0,
}


# Contracts executed inside the probe contract below.  Extend this mapping with
# additional entries whenever new bridge modules are surfaced to contracts.  The
# probe transaction executes each ``statement`` which stores a deterministic
# fingerprint derived from that module into application state.  The statements
# rely on the globals exposed by the contracting stdlib environment (for
# example ``hashlib`` and ``datetime``) so that the compiler accepts them
# without needing ``import`` statements.
MODULE_PROBES = [
    {
        "statement": "module_results['hashing'] = hashlib.sha3('determinism')",
    },
    {
        "statement": "module_results['decimal'] = str(decimal('123.456789'))",
    },
    {
        "statement": "module_results['time'] = str(datetime.datetime(2024, 1, 1))",
    },
]


def _base_transaction(
    *,
    sender: str,
    contract: str,
    function: str,
    nonce: int,
    kwargs: Dict[str, object],
    stamps_supplied: int = 1000,
    signature: str = DEFAULT_SIGNATURE,
) -> Dict[str, object]:
    return {
        "payload": {
            "chain_id": CHAIN_ID,
            "contract": contract,
            "function": function,
            "kwargs": kwargs,
            "nonce": nonce,
            "sender": sender,
            "stamps_supplied": stamps_supplied,
        },
        "metadata": {"signature": signature},
    }


def _encode_transaction_bytes(tx_str: str) -> bytes:
    tx_bytes = tx_str.encode("utf-8")
    tx_hex = binascii.hexlify(tx_bytes).decode("utf-8")
    return tx_hex.encode("utf-8")


def _encode_block_transactions(txs: Sequence[Dict[str, object]]) -> List[bytes]:
    encoded: List[bytes] = []
    for tx in txs:
        tx_str = json.dumps(tx, separators=(",", ":"), sort_keys=True)
        encoded.append(_encode_transaction_bytes(tx_str))
    return encoded


def _make_request(height: int, txs: Sequence[Dict[str, object]], *, base_seconds: int) -> Request:
    timestamp = Timestamp(seconds=base_seconds + height, nanos=height)
    return Request(
        finalize_block=RequestFinalizeBlock(
            height=height,
            txs=_encode_block_transactions(txs),
            time=timestamp,
        )
    )


def _module_probe_contract() -> str:
    import_lines: List[str] = []
    for probe in MODULE_PROBES:
        for import_line in probe.get("imports", ()):  # type: ignore[arg-type]
            if import_line not in import_lines:
                import_lines.append(import_line)

    statements = [probe["statement"] for probe in MODULE_PROBES]
    imports_block = "\n".join(import_lines)
    statements_block = "\n    ".join(statements)

    return f"""{imports_block}

module_results = Hash()
probe_heights = Variable()

@construct
def seed():
    module_results['constructor'] = 'seeded'
    probe_heights.set([])

@export
def probe(height: int):
    history = probe_heights.get()
    if history is None:
        history = []
    history = history + [height]
    probe_heights.set(history)
    {statements_block}
    return history
"""


def _build_module_probe_blocks() -> List[List[Dict[str, object]]]:
    contract_code = _module_probe_contract()
    blocks: List[List[Dict[str, object]]] = []

    blocks.append(
        [
            _base_transaction(
                sender="sys",
                contract="submission",
                function="submit_contract",
                nonce=1,
                kwargs={
                    "name": "con_module_probe",
                    "code": contract_code,
                    "constructor_args": {},
                    "owner": "sys",
                },
                stamps_supplied=2_000,
            )
        ]
    )

    blocks.append(
        [
            _base_transaction(
                sender="sys",
                contract="con_module_probe",
                function="probe",
                nonce=2,
                kwargs={"height": 1},
                stamps_supplied=1_500,
            )
        ]
    )

    blocks.append(
        [
            _base_transaction(
                sender="sys",
                contract="con_module_probe",
                function="probe",
                nonce=3,
                kwargs={"height": 2},
                stamps_supplied=1_500,
            )
        ]
    )

    return blocks


def _build_currency_blocks(starting_nonce: int = 100) -> List[List[Dict[str, object]]]:
    blocks: List[List[Dict[str, object]]] = []

    blocks.append(
        [
            _base_transaction(
                sender="multi_node_operator",
                contract="currency",
                function="transfer",
                nonce=starting_nonce,
                kwargs={"amount": 750, "to": "module_probe_receiver"},
                stamps_supplied=1_000,
            )
        ]
    )

    blocks.append(
        [
            _base_transaction(
                sender="module_probe_receiver",
                contract="currency",
                function="approve",
                nonce=starting_nonce + 1,
                kwargs={"amount": 300, "to": "sys"},
                stamps_supplied=1_000,
            )
        ]
    )

    blocks.append(
        [
            _base_transaction(
                sender="sys",
                contract="currency",
                function="transfer",
                nonce=starting_nonce + 2,
                kwargs={"amount": 125, "to": "multi_node_operator"},
                stamps_supplied=1_000,
            )
        ]
    )

    return blocks


def _build_requests(blocks: Iterable[List[Dict[str, object]]], *, start_height: int, base_seconds: int) -> List[Request]:
    requests: List[Request] = []
    for index, txs in enumerate(blocks):
        height = start_height + index
        requests.append(_make_request(height, txs, base_seconds=base_seconds))
    return requests


def load_multi_node_scenarios() -> Dict[str, List[Request]]:
    """Return the scenarios executed by the multi-node tests."""

    module_blocks = _build_module_probe_blocks()
    currency_blocks = _build_currency_blocks()

    scenarios: Dict[str, List[Request]] = {
        "module_probe": _build_requests(module_blocks, start_height=1, base_seconds=1_720_000_000),
        "currency_flow": _build_requests(currency_blocks, start_height=10, base_seconds=1_720_000_100),
    }

    combined_blocks = module_blocks + currency_blocks
    scenarios["combined"] = _build_requests(combined_blocks, start_height=1, base_seconds=1_720_000_200)

    return scenarios


__all__ = [
    "CHAIN_ID",
    "DEFAULT_SIGNATURE",
    "MODULE_PROBES",
    "SCENARIO_ACCOUNT_BALANCES",
    "load_multi_node_scenarios",
]
