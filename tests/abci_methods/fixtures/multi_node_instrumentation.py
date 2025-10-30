"""Helpers that instrument the Xian app for deterministic multi-node tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from types import MethodType
from typing import Callable, List, Sequence

from xian.utils.encoding import stringify_decimals


class _FilteredFingerprintList(list):
    """List wrapper that skips failed transaction hashes for tests."""

    __slots__ = ("_app",)

    def __init__(self, app, initial: Sequence[str]):
        super().__init__(initial)
        self._app = app

    def append(self, value: str) -> None:  # pragma: no cover - trivial wrapper
        if getattr(self._app, "_skip_next_fingerprint", False):
            self._app._skip_next_fingerprint = False
            return

        self._app._skip_next_fingerprint = False
        super().append(value)


def attach_failed_tx_fingerprint_filter(app) -> Callable[[], None]:
    """Ensure failed tx hashes do not affect app fingerprints during tests."""

    original_fingerprints = app.fingerprint_hashes
    original_commit = app.commit

    app._skip_next_fingerprint = False
    app.fingerprint_hashes = _FilteredFingerprintList(app, list(original_fingerprints))

    async def commit_with_filter(self):
        response = await original_commit()
        self._skip_next_fingerprint = False
        self.fingerprint_hashes = _FilteredFingerprintList(self, [])
        return response

    app.commit = MethodType(commit_with_filter, app)

    def restore() -> None:
        app.commit = original_commit
        app.fingerprint_hashes = original_fingerprints
        if hasattr(app, "_skip_next_fingerprint"):
            delattr(app, "_skip_next_fingerprint")

    return restore


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
            app._skip_next_fingerprint = True
            return result

        tx_result = result.get("tx_result")
        if not tx_result:
            app._skip_next_fingerprint = True
            return result

        status = tx_result.get("status")
        app._skip_next_fingerprint = status is not None and status != 0
        if status and status != 0:
            return result

        normalized_state = [
            entry
            for entry in tx_result.get("state", [])
            if not entry["key"].startswith("currency.balances:")
        ]
        if len(normalized_state) != len(tx_result.get("state", [])):
            tx_result = dict(tx_result)
            tx_result["state"] = normalized_state

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


__all__ = [
    "StateFingerprintRecorder",
    "attach_failed_tx_fingerprint_filter",
    "attach_state_fingerprint_recorder",
]
