"""Helpers that instrument the Xian app for deterministic multi-node tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from types import MethodType
from typing import Callable, List, Sequence

from xian.utils.encoding import stringify_decimals


@dataclass
class StateFingerprintRecorder:
    """Collects per-transaction state fingerprints without mutating the app."""

    processor: object
    original_process_tx: Callable
    _current_block: List[str] = field(default_factory=list)
    _blocks: List[str] = field(default_factory=list)

    def begin_block(self) -> None:
        self._current_block = []

    def finish_block(self) -> str:
        digest = hashlib.sha3_256("".join(self._current_block).encode("utf-8")).hexdigest()
        self._blocks.append(digest)
        self._current_block = []
        return digest

    @property
    def block_fingerprints(self) -> Sequence[str]:
        return tuple(self._blocks)

    def restore(self) -> None:
        self.processor.process_tx = self.original_process_tx


def attach_state_fingerprint_recorder(app) -> StateFingerprintRecorder:
    """Wrap ``process_tx`` so tests can inspect deterministic state hashes."""

    processor = app.tx_processor
    original_process_tx = processor.process_tx
    recorder = StateFingerprintRecorder(processor=processor, original_process_tx=original_process_tx)

    def process_tx_with_recording(self, tx, enabled_fees=False, rewards_handler=None):
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
        recorder._current_block.append(state_fingerprint)
        return result

    processor.process_tx = MethodType(process_tx_with_recording, processor)

    def restore() -> None:
        recorder.restore()

    recorder.cleanup = restore  # type: ignore[attr-defined]

    return recorder


__all__ = ["StateFingerprintRecorder", "attach_state_fingerprint_recorder"]
