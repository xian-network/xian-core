"""Helpers that instrument the Xian app for deterministic multi-node tests."""

from __future__ import annotations

import hashlib
import json
from types import MethodType
from typing import Callable

from xian.utils.encoding import stringify_decimals


def attach_state_fingerprint_to_tx_hashes(app) -> Callable[[], None]:
    """Augment ``tx_processor.process_tx`` so tx hashes reflect state writes."""

    processor = app.tx_processor
    original_process_tx = processor.process_tx

    def process_tx_with_state_fingerprint(self, tx, enabled_fees=False, rewards_handler=None):
        result = original_process_tx(tx, enabled_fees=enabled_fees, rewards_handler=rewards_handler)
        if not result:
            return result

        tx_result = result.get("tx_result")
        if not tx_result:
            return result

        canonical_result = json.dumps(
            stringify_decimals(tx_result),
            sort_keys=True,
            separators=(",", ":"),
        )
        state_fingerprint = hashlib.sha3_256(canonical_result.encode("utf-8")).hexdigest()
        combined_hash = hashlib.sha3_256(
            (tx_result["hash"] + state_fingerprint).encode("utf-8")
        ).hexdigest()
        tx_result["hash"] = combined_hash
        return result

    processor.process_tx = MethodType(process_tx_with_state_fingerprint, processor)

    def restore() -> None:
        processor.process_tx = original_process_tx

    return restore


__all__ = ["attach_state_fingerprint_to_tx_hashes"]
