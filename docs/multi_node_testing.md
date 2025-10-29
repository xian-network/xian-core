# Multi-node ABCI test harness

The multi-node tests under `tests/abci_methods/` replay the same block flow
against multiple isolated Xian application instances.  Each node boots with its
own CometBFT home directory so that the resulting `app_hash` values can be
compared after every block.  This harness lets us detect non-deterministic
behavior—such as bridge modules that depend on local machine state—before code
ships to production.

## How scenarios are assembled

* `tests/abci_methods/fixtures/multi_node.py` clones the single-node fixture
  directory for as many nodes as a test requires and temporarily swaps the
  global constants cache so every node reads and writes inside its own home.
* `tests/abci_methods/fixtures/multi_node_scenarios.py` defines reusable
  sequences of `RequestFinalizeBlock` messages.  These requests are grouped into
  **scenarios** which the tests load via `load_multi_node_scenarios()`.
* `tests/abci_methods/fixtures/multi_node_instrumentation.py` wraps the
  transaction processor and records a deterministic fingerprint of every write
  each block produces.  The recorder never mutates the application, so the
  production `finalize_block` implementation stays untouched while tests gain
  the extra state visibility they need to spot divergence.
* `tests/abci_methods/test_multi_node_app_hash.py` consumes those scenarios,
  seeds deterministic balances, and compares the final `app_hash` emitted by
  each node.  The module-probe scenario optionally mutates a bridge module to
  prove that divergent state fingerprints are surfaced.

## Adding coverage for a new bridge module

The module-probe scenario is driven by the `MODULE_PROBES` list.  Each entry
injects import statements and snippets that run inside the probe contract.
Follow these steps to exercise a new module:

1. Edit `MODULE_PROBES` in
   `tests/abci_methods/fixtures/multi_node_scenarios.py` and append a new entry.
   Specify any imports that the contract needs (for example,
   `"from contracting.stdlib.bridge.crypto import keccak"`) and write a
   statement that stores a deterministic fingerprint in `module_results`.
2. Keep the statement side-effect free besides writing to
   `module_results[...]`.  The probe contract executes the statement in two
   separate blocks so the value must not depend on local clocks or entropy.
3. If the module requires account balances or permissions, extend
   `SCENARIO_ACCOUNT_BALANCES` in the same file so that
   `TestMultiNodeAppHash._seed_account_balances` prepares matching state on
   every node.
4. Run `PYTHONPATH=src pytest tests/abci_methods/test_multi_node_app_hash.py -q`
   to ensure the scenario executes deterministically.  When optional dependencies
   such as `contracting` are missing the suite will skip instead of running.  The
   recorder will surface any non-deterministic state writes even if the
   production `app_hash` value does not yet reflect them.

## Creating additional block flows

Some features are easier to validate with their own block sequence instead of
piggybacking on the module probe.  To add a brand-new scenario:

1. Write helper functions next to `_build_currency_blocks()` that return a list
   of blocks, where each block is a list of transaction dictionaries compatible
   with `_base_transaction()`.
2. Convert the blocks into ABCI requests with `_build_requests(...)` and store
   the result in the `scenarios` dictionary returned by
   `load_multi_node_scenarios()`.
3. Add an assertion in `tests/abci_methods/test_multi_node_app_hash.py` if the
   new scenario needs bespoke validation beyond hash comparison (for example,
   checking event payloads or specific account balances).

The tests automatically discover every scenario exposed by
`load_multi_node_scenarios()`, so no additional registration is required.
