"""
Simple integration helper for Xian ABCI debugging.

This module provides easy-to-use functions to add state divergence debugging
to your existing Xian ABCI application with minimal code changes.
"""

import functools
from typing import Optional, Any, Dict
from loguru import logger

from .core.debugger import StateDebugger
from .core.config import DebuggerConfig


class XianDebuggerIntegration:
    """Helper class to integrate debugger with Xian ABCI app"""
    
    def __init__(self, abci_app):
        self.abci_app = abci_app
        self.debugger: Optional[StateDebugger] = None
        self._init_debugger()
    
    def _init_debugger(self):
        """Initialize the debugger if enabled"""
        try:
            config = DebuggerConfig()
            if config.enabled:
                self.debugger = StateDebugger(config)
                self.debugger.start()
                logger.info("Xian state divergence debugger enabled")
            else:
                logger.info("Xian state divergence debugger disabled (set XIAN_DEBUGGER_ENABLED=true to enable)")
        except Exception as e:
            logger.error(f"Failed to initialize Xian debugger: {e}")
            self.debugger = None
    
    def debug_context(self, operation_name: str, **context_data):
        """Create a debug context for an operation"""
        if self.debugger:
            try:
                return self.debugger.debug_context(operation_name, **context_data)
            except Exception as e:
                logger.error(f"Error creating debug context for {operation_name}: {e}")
                return NoOpContext()
        else:
            # Return a no-op context manager
            return NoOpContext()
    
    def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit a debugging event"""
        if self.debugger:
            try:
                self.debugger.emit_event(event_type, data)
            except Exception as e:
                logger.error(f"Error emitting debug event {event_type}: {e}")
    
    def instrument_abci_method(self, method_name: str):
        """Decorator to instrument ABCI methods"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract request info if available
                context_data = {"method": method_name}
                if args and hasattr(args[0], 'height'):
                    context_data["block_height"] = args[0].height
                if args and hasattr(args[0], 'txs'):
                    context_data["tx_count"] = len(args[0].txs)
                
                with self.debug_context(method_name, **context_data):
                    result = await func(*args, **kwargs)
                    
                    # Emit method completion event
                    self.emit_event(f"{method_name}_completed", {
                        **context_data,
                        "success": True
                    })
                    
                    return result
            return wrapper
        return decorator


class NoOpContext:
    """No-operation context manager for when debugger is disabled"""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def setup_xian_debugging(abci_app) -> XianDebuggerIntegration:
    """
    Set up debugging for a Xian ABCI application.
    
    Usage:
        # In your xian_abci.py __init__ method:
        from xian.debugger.xian_integration import setup_xian_debugging
        
        class Xian:
            def __init__(self, constants=Constants()):
                # ... your existing code ...
                
                # Add this line to enable debugging
                self.debug_integration = setup_xian_debugging(self)
    
    Args:
        abci_app: Your Xian ABCI application instance
        
    Returns:
        XianDebuggerIntegration instance
    """
    return XianDebuggerIntegration(abci_app)


def debug_abci_method(integration: XianDebuggerIntegration, method_name: str):
    """
    Decorator to add debugging to ABCI methods.
    
    Usage:
        @debug_abci_method(self.debug_integration, "finalize_block")
        async def finalize_block(self, req):
            # Your existing method code
            pass
    """
    return integration.instrument_abci_method(method_name)


# Convenience functions for common debugging scenarios

def debug_state_change(integration: XianDebuggerIntegration, 
                      block_height: int, 
                      app_hash: Optional[str] = None,
                      tx_count: int = 0):
    """Emit a state change event"""
    integration.emit_event("state_change", {
        "block_height": block_height,
        "app_hash": app_hash,
        "tx_count": tx_count
    })


def debug_transaction_processed(integration: XianDebuggerIntegration,
                               tx_hash: str,
                               success: bool,
                               gas_used: int = 0):
    """Emit a transaction processed event"""
    integration.emit_event("transaction_processed", {
        "tx_hash": tx_hash,
        "success": success,
        "gas_used": gas_used
    })


def debug_cache_operation(integration: XianDebuggerIntegration,
                         operation: str,
                         cache_size: int,
                         cache_type: str = "driver"):
    """Emit a cache operation event"""
    integration.emit_event("cache_operation", {
        "operation": operation,
        "cache_size": cache_size,
        "cache_type": cache_type
    })