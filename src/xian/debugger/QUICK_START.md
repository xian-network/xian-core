# 🚀 Quick Start: Enable Debugging in Your Xian ABCI App

## TL;DR - 3 Steps to Enable Debugging

### 1. Set Environment Variables
```bash
export XIAN_DEBUGGER_ENABLED=true
export XIAN_DEBUG_LEVEL=standard
```

### 2. Add One Import to xian_abci.py
```python
from xian.debugger.xian_integration import setup_xian_debugging
```

### 3. Add One Line to Your Xian.__init__() Method
```python
class Xian:
    def __init__(self, constants=Constants()):
        # ... your existing code ...
        
        # Add this line at the end:
        self.debug_integration = setup_xian_debugging(self)
```

**That's it!** Your debugger is now active and monitoring for state divergence issues.

## What You'll See

When you start your node, you'll see:
```
INFO xian.debugger Xian state divergence debugger enabled
INFO xian.debugger.monitors.state_tracker State tracker initialized
INFO xian.debugger.monitors.cache_monitor Cache monitor initialized
```

If issues are detected, you'll see warnings/errors like:
```
ERROR xian.debugger.monitors.state_tracker App hash mismatch detected at block 12345
WARNING xian.debugger.monitors.cache_monitor Cache leak detected: 5 entries not cleaned
```

## Optional: Add Method Instrumentation

For more detailed debugging, wrap your ABCI methods:

```python
async def finalize_block(self, req):
    with self.debug_integration.debug_context("finalize_block", 
                                             block_height=req.height):
        res = await finalize_block.finalize_block(self, req)
        
        # Emit debugging event
        self.debug_integration.emit_event("state_change", {
            "block_height": req.height,
            "app_hash": res.app_hash.hex() if res.app_hash else None
        })
        
        return res
```

## Configuration Options

```bash
# Basic
export XIAN_DEBUGGER_ENABLED=true          # Enable/disable
export XIAN_DEBUG_LEVEL=standard           # minimal, standard, comprehensive

# Advanced
export XIAN_DEBUGGER_MAX_MEMORY_MB=100     # Memory limit
export XIAN_DEBUGGER_SAMPLE_RATE=1.0      # Sampling rate (0.0-1.0)
export XIAN_DEBUGGER_OUTPUT_FORMAT=json   # json, text, markdown
```

## What Gets Monitored

✅ **State Changes**: App hash divergence detection  
✅ **Cache Leaks**: Driver cache pollution monitoring  
✅ **JSON Failures**: Silent decode error detection  
✅ **Non-determinism**: Inconsistent execution detection  
✅ **Transaction Processing**: Execution consistency monitoring  

## Need Help?

- See `INTEGRATION_GUIDE.md` for detailed instructions
- See `SIMPLE_INTEGRATION_EXAMPLE.py` for copy-paste examples
- Check the logs for `xian.debugger` messages

## Disable Debugging

Set `XIAN_DEBUGGER_ENABLED=false` or remove the environment variable.