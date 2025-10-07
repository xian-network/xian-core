# Xian ABCI Debugger Integration Guide

This guide shows you exactly how to enable the state divergence debugger in your `xian_abci.py` application.

## Quick Start (Recommended)

### Step 1: Enable the Debugger

Add these environment variables to enable debugging:

```bash
# Enable the debugger
export XIAN_DEBUGGER_ENABLED=true

# Set debug level (minimal, standard, comprehensive)
export XIAN_DEBUG_LEVEL=standard

# Set monitoring scope (transaction, block, both)
export XIAN_MONITORING_SCOPE=both
```

### Step 2: Modify your xian_abci.py

Add the debugger integration to your `Xian` class. Here's what to add:

```python
# Add this import at the top with other imports
from xian.debugger import StateDebugger, DebuggerConfig

class Xian:
    def __init__(self, constants=Constants()):
        # ... your existing initialization code ...
        
        # Add debugger initialization AFTER your existing __init__ code
        self.debugger = None
        self._init_debugger()
    
    def _init_debugger(self):
        """Initialize the state divergence debugger"""
        try:
            config = DebuggerConfig()
            if config.enabled:
                self.debugger = StateDebugger(config)
                self.debugger.start()
                logger.info("State divergence debugger enabled")
            else:
                logger.info("State divergence debugger disabled")
        except Exception as e:
            logger.error(f"Failed to initialize debugger: {e}")
            self.debugger = None
```

### Step 3: Add Instrumentation to ABCI Methods

Modify your ABCI methods to include debugging. Here's an example for `finalize_block`:

```python
async def finalize_block(self, req):
    """
    Contains the fields of the newly decided block.
    """
    # Add debugging context
    if self.debugger:
        with self.debugger.debug_context("finalize_block", 
                                       block_height=req.height,
                                       tx_count=len(req.txs)):
            res = await finalize_block.finalize_block(self, req)
            
            # Emit state change event
            self.debugger.emit_event("state_change", {
                "block_height": req.height,
                "app_hash": res.app_hash.hex() if res.app_hash else None,
                "tx_count": len(req.txs)
            })
            return res
    else:
        res = await finalize_block.finalize_block(self, req)
        return res
```

## Complete Integration Example

Here's a complete example showing how to modify your `xian_abci.py`:

```python
import os
import importlib
import sys
import gc
import asyncio
import signal

from loguru import logger
from datetime import timedelta, datetime
from abci.server import ABCIServer
from xian.constants import Constants
from xian.services.bds.bds import BDS
from contracting.client import ContractingClient

# Add debugger import
from xian.debugger import StateDebugger, DebuggerConfig

# ... your other imports ...

class Xian:
    def __init__(self, constants=Constants()):
        # ... your existing initialization code ...
        
        # Initialize debugger
        self.debugger = None
        self._init_debugger()
    
    def _init_debugger(self):
        """Initialize the state divergence debugger"""
        try:
            config = DebuggerConfig()
            if config.enabled:
                self.debugger = StateDebugger(config)
                self.debugger.start()
                logger.info("State divergence debugger enabled")
            else:
                logger.info("State divergence debugger disabled")
        except Exception as e:
            logger.error(f"Failed to initialize debugger: {e}")
            self.debugger = None

    async def finalize_block(self, req):
        """Instrumented finalize_block with debugging"""
        if self.debugger:
            with self.debugger.debug_context("finalize_block", 
                                           block_height=req.height,
                                           tx_count=len(req.txs)):
                res = await finalize_block.finalize_block(self, req)
                
                # Emit debugging events
                self.debugger.emit_event("state_change", {
                    "block_height": req.height,
                    "app_hash": res.app_hash.hex() if res.app_hash else None,
                    "tx_count": len(req.txs)
                })
                return res
        else:
            return await finalize_block.finalize_block(self, req)

    async def commit(self):
        """Instrumented commit with debugging"""
        if self.debugger:
            with self.debugger.debug_context("commit"):
                res = await commit.commit(self)
                
                # Emit commit event
                self.debugger.emit_event("commit", {
                    "app_hash": res.data.hex() if res.data else None
                })
                return res
        else:
            return await commit.commit(self)

    async def check_tx(self, raw_tx):
        """Instrumented check_tx with debugging"""
        if self.debugger:
            with self.debugger.debug_context("check_tx"):
                return await check_tx.check_tx(self, raw_tx)
        else:
            return await check_tx.check_tx(self, raw_tx)

    # Add similar instrumentation to other ABCI methods as needed...
```

## Configuration Options

You can configure the debugger using environment variables:

```bash
# Basic settings
export XIAN_DEBUGGER_ENABLED=true          # Enable/disable debugger
export XIAN_DEBUG_LEVEL=standard           # minimal, standard, comprehensive
export XIAN_MONITORING_SCOPE=both          # transaction, block, both

# Advanced settings
export XIAN_DEBUGGER_MAX_MEMORY_MB=100     # Memory limit
export XIAN_DEBUGGER_MAX_CPU_PERCENT=5    # CPU usage limit
export XIAN_DEBUGGER_SAMPLE_RATE=1.0      # Sampling rate (0.0-1.0)

# Output settings
export XIAN_DEBUGGER_LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR
export XIAN_DEBUGGER_OUTPUT_FORMAT=json   # json, text, markdown
```

## What the Debugger Monitors

Once enabled, the debugger will automatically monitor:

1. **State Changes**: Tracks state modifications and app hash changes
2. **Cache Usage**: Monitors Driver cache for leaks and pollution
3. **JSON Operations**: Validates JSON encoding/decoding operations
4. **Determinism**: Checks for non-deterministic operations
5. **Transaction Processing**: Monitors transaction execution consistency

## Viewing Debug Output

Debug information is logged using the existing logger. Look for messages like:

```
2024-01-01 12:00:00 INFO xian.debugger State divergence debugger enabled
2024-01-01 12:00:01 WARNING xian.debugger.monitors.cache_monitor Cache leak detected: 5 entries not cleaned
2024-01-01 12:00:02 ERROR xian.debugger.monitors.state_tracker App hash mismatch detected at block 12345
```

## Minimal Integration (If You Want Less Overhead)

If you want minimal overhead, you can enable only specific monitors:

```python
def _init_debugger(self):
    """Initialize debugger with only state tracking"""
    try:
        config = DebuggerConfig()
        if config.enabled:
            self.debugger = StateDebugger(config)
            # Only enable state tracker
            self.debugger.plugin_manager.enable_plugin('state_tracker')
            self.debugger.plugin_manager.disable_plugin('cache_monitor')
            self.debugger.plugin_manager.disable_plugin('json_validator')
            self.debugger.plugin_manager.disable_plugin('determinism_validator')
            self.debugger.start()
            logger.info("Minimal state debugger enabled")
    except Exception as e:
        logger.error(f"Failed to initialize debugger: {e}")
        self.debugger = None
```

## Testing the Integration

1. Start your node with debugging enabled:
   ```bash
   export XIAN_DEBUGGER_ENABLED=true
   python src/xian/xian_abci.py
   ```

2. Look for the initialization message:
   ```
   State divergence debugger enabled
   ```

3. Process some transactions and check for debug output in your logs.

## Troubleshooting

**Q: I don't see any debug output**
A: Make sure `XIAN_DEBUGGER_ENABLED=true` is set and check your log level.

**Q: The debugger is using too much memory**
A: Set `XIAN_DEBUGGER_MAX_MEMORY_MB=50` to limit memory usage.

**Q: I want to disable specific monitors**
A: Use the minimal integration example above to selectively enable monitors.

**Q: How do I know if state divergence is detected?**
A: Look for ERROR level messages from `xian.debugger.monitors.state_tracker` in your logs.