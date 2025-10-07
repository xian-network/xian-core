"""
Xian State Divergence Debugger

A comprehensive debugging system for detecting and analyzing app hash state divergence
issues in the Xian blockchain network.
"""

from .core.debugger import StateDebugger
from .core.config import DebuggerConfig
from .core.events import DebugEvent, EventType
from .xian_integration import setup_xian_debugging, XianDebuggerIntegration

__version__ = "1.0.0"
__all__ = [
    "StateDebugger", 
    "DebuggerConfig", 
    "DebugEvent", 
    "EventType",
    "setup_xian_debugging",
    "XianDebuggerIntegration"
]