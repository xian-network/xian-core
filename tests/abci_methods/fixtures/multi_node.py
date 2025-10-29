"""Utilities for running multi-node style tests in the ABCI suite.

These helpers allow tests to spin up multiple ``Xian`` application instances
that each operate on their own isolated CometBFT home directory.  The default
test fixtures only support a single node living at ``/tmp/cometbft`` which
makes it impossible to compare state fingerprints (app hashes) across nodes.

The helpers defined here clone the existing fixture directory for every node
and temporarily patch the global ``Constants`` references so that the Xian
runtime reads and writes inside the node specific directory.  This enables
tests to execute the exact same block on many nodes and compare the resulting
app hash to catch divergences before deploying to production.
"""

from __future__ import annotations

import contextlib
from importlib import import_module
from pathlib import Path
import shutil
from typing import Iterator, List, Tuple, Type

from .mock_constants import MockConstants

FIXTURE_DIR = Path(__file__).resolve().parent / ".cometbft-fixture"
MULTI_NODE_ROOT = Path("/tmp/cometbft-multi/")

# Modules that cache ``Constants`` as ``c`` at import time and therefore must
# be patched whenever we want to point the application at a different CometBFT
# home directory.
MODULES_WITH_CONSTANTS = (
    "xian.utils.block",
    "xian.nonce",
    "xian.methods.query",
    "xian.methods.check_tx",
    "xian.services.simulator",
    "xian.tools.configure",
)


def _build_constants(node_home: Path) -> Type[MockConstants]:
    """Create a ``MockConstants`` subclass targeting ``node_home``.

    The generated class mirrors ``MockConstants`` but with all filesystem
    locations rooted inside the provided directory.  A brand new subclass is
    generated on every invocation so that multiple nodes can safely coexist.
    """

    attributes = {
        "COMETBFT_HOME": node_home,
        "COMETBFT_CONFIG": node_home / "config/config.toml",
        "COMETBFT_GENESIS": node_home / "config/genesis.json",
        "STORAGE_HOME": node_home / "xian/",
    }

    return type(
        f"MultiNodeMockConstants_{node_home.name}",
        (MockConstants,),
        attributes,
    )


def setup_multi_node_fixtures(node_count: int) -> List[Path]:
    """Clone the default CometBFT fixture for ``node_count`` nodes."""

    if node_count < 1:
        raise ValueError("node_count must be at least 1")

    if MULTI_NODE_ROOT.exists():
        shutil.rmtree(MULTI_NODE_ROOT)

    node_homes: List[Path] = []
    for index in range(node_count):
        node_home = MULTI_NODE_ROOT / f"node-{index}"
        shutil.copytree(FIXTURE_DIR, node_home)
        node_homes.append(node_home)

    return node_homes


def teardown_multi_node_fixtures() -> None:
    """Remove all directories created by :func:`setup_multi_node_fixtures`."""

    if MULTI_NODE_ROOT.exists():
        shutil.rmtree(MULTI_NODE_ROOT)


@contextlib.contextmanager
def use_node_constants(node_home: Path) -> Iterator[Type[MockConstants]]:
    """Context manager that points global constants to ``node_home``.

    The Xian code base keeps references to :class:`~xian.constants.Constants`
    (often imported as ``c``) in several modules.  To run multiple nodes in the
    same process we need to temporarily replace those references so that all
    file access happens inside the node specific fixture directory.
    """

    node_constants = _build_constants(node_home)

    constants_module = import_module("xian.constants")
    original_constants = constants_module.Constants
    constants_module.Constants = node_constants

    patched_modules: List[Tuple[object, object]] = []
    for module_name in MODULES_WITH_CONSTANTS:
        module = import_module(module_name)
        if hasattr(module, "c"):
            patched_modules.append((module, module.c))
            module.c = node_constants

    try:
        yield node_constants
    finally:
        constants_module.Constants = original_constants
        for module, original in patched_modules:
            module.c = original

