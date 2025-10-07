"""
SIMPLE INTEGRATION EXAMPLE

This shows exactly what to add to your xian_abci.py to enable debugging.
Copy and paste these changes into your existing file.
"""

# ============================================================================
# STEP 1: Add this import at the top of your xian_abci.py file
# ============================================================================

from xian.debugger.xian_integration import setup_xian_debugging


# ============================================================================
# STEP 2: Add this to your Xian class __init__ method
# ============================================================================

class Xian:
    def __init__(self, constants=Constants()):
        # ... your existing initialization code ...
        
        # ADD THIS LINE - Initialize debugger (add after all your existing init code)
        self.debug_integration = setup_xian_debugging(self)


# ============================================================================
# STEP 3: Modify your ABCI methods to include debugging (OPTIONAL but recommended)
# ============================================================================

    async def finalize_block(self, req):
        """
        Contains the fields of the newly decided block.
        This method is equivalent to the call sequence BeginBlock, [DeliverTx], and EndBlock in the previous version of ABCI.
        """
        # ADD THIS - Debug context for the operation
        with self.debug_integration.debug_context("finalize_block", 
                                                 block_height=req.height,
                                                 tx_count=len(req.txs)):
            res = await finalize_block.finalize_block(self, req)
            
            # ADD THIS - Emit state change event
            self.debug_integration.emit_event("state_change", {
                "block_height": req.height,
                "app_hash": res.app_hash.hex() if res.app_hash else None,
                "tx_count": len(req.txs)
            })
            
            return res

    async def commit(self):
        """
        Signal the Application to persist the application state.
        """
        # ADD THIS - Debug context for commit
        with self.debug_integration.debug_context("commit"):
            res = await commit.commit(self)
            
            # ADD THIS - Emit commit event
            self.debug_integration.emit_event("commit", {
                "app_hash": res.data.hex() if res.data else None
            })
            
            return res

    async def check_tx(self, raw_tx):
        """
        Guardian of the mempool: every node runs CheckTx before letting a transaction into its local mempool.
        """
        # ADD THIS - Debug context for transaction checking
        with self.debug_integration.debug_context("check_tx"):
            res = await check_tx.check_tx(self, raw_tx)
            return res


# ============================================================================
# STEP 4: Set environment variables to enable debugging
# ============================================================================

"""
Before running your application, set these environment variables:

export XIAN_DEBUGGER_ENABLED=true
export XIAN_DEBUG_LEVEL=standard
export XIAN_MONITORING_SCOPE=both

Then run your application normally:
python src/xian/xian_abci.py
"""


# ============================================================================
# COMPLETE MINIMAL EXAMPLE
# ============================================================================

"""
Here's what your modified xian_abci.py should look like with minimal changes:

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

# ADD THIS IMPORT
from xian.debugger.xian_integration import setup_xian_debugging

# ... all your other existing imports ...

class Xian:
    def __init__(self, constants=Constants()):
        # ... all your existing initialization code ...
        
        # ADD THIS LINE at the end of __init__
        self.debug_integration = setup_xian_debugging(self)

    # ... all your existing methods ...

    async def finalize_block(self, req):
        # ADD debugging wrapper
        with self.debug_integration.debug_context("finalize_block", 
                                                 block_height=req.height,
                                                 tx_count=len(req.txs)):
            res = await finalize_block.finalize_block(self, req)
            
            # Emit debugging event
            self.debug_integration.emit_event("state_change", {
                "block_height": req.height,
                "app_hash": res.app_hash.hex() if res.app_hash else None,
                "tx_count": len(req.txs)
            })
            
            return res

    # ... rest of your existing code unchanged ...

# Your existing main() function and everything else stays the same
"""


# ============================================================================
# WHAT YOU'LL SEE IN THE LOGS
# ============================================================================

"""
When you run with debugging enabled, you'll see messages like:

2024-01-01 12:00:00 INFO xian.debugger Xian state divergence debugger enabled
2024-01-01 12:00:01 INFO xian.debugger.monitors.state_tracker State tracker initialized
2024-01-01 12:00:02 INFO xian.debugger.monitors.cache_monitor Cache monitor initialized
2024-01-01 12:00:03 DEBUG xian.debugger Entering debug context: finalize_block (block_height=12345)
2024-01-01 12:00:04 INFO xian.debugger State change detected at block 12345
2024-01-01 12:00:05 WARNING xian.debugger.monitors.cache_monitor Cache size increased: 150 entries

If there are issues, you'll see ERROR messages like:
2024-01-01 12:00:06 ERROR xian.debugger.monitors.state_tracker App hash mismatch detected!
"""