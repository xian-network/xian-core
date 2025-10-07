"""
Instrumentation Utilities

Provides decorators and utilities for instrumenting existing code
to work with the state divergence debugger.
"""

import functools
import time
import json
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from loguru import logger

from ..core.debugger import get_debugger
from ..core.events import DebugEvent, EventType, Severity

F = TypeVar('F', bound=Callable[..., Any])


def instrument_abci_method(method_name: str):
    """
    Decorator to instrument ABCI methods for debugging.
    
    Args:
        method_name: Name of the ABCI method being instrumented
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            debugger = get_debugger()
            if not debugger or not debugger.is_running:
                return func(*args, **kwargs)
            
            start_time = time.time()
            
            try:
                # Extract relevant data from arguments
                context_data = _extract_abci_context(method_name, args, kwargs)
                
                # Set debugger context
                debugger.set_context(
                    block_height=context_data.get('block_height'),
                    transaction_hash=context_data.get('transaction_hash')
                )
                
                # Call appropriate debugger hook
                if method_name == 'finalize_block':
                    debugger.on_block_start(
                        context_data.get('block_height', 0),
                        context_data
                    )
                elif method_name == 'commit':
                    debugger.on_commit(
                        context_data.get('block_height', 0),
                        context_data.get('app_hash', '')
                    )
                
                # Execute the original method
                result = func(*args, **kwargs)
                
                # Post-execution hooks
                if method_name == 'finalize_block':
                    app_hash = _extract_app_hash_from_result(result)
                    debugger.on_block_end(
                        context_data.get('block_height', 0),
                        app_hash
                    )
                
                return result
                
            except Exception as e:
                # Log error and re-raise
                if debugger:
                    error_event = DebugEvent(
                        event_type=EventType.TRANSACTION_ERROR,
                        severity=Severity.HIGH,
                        message=f"Error in {method_name}: {str(e)}",
                        data={
                            'method': method_name,
                            'error': str(e),
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        }
                    )
                    debugger.event_bus.emit(error_event)
                raise
            
            finally:
                # Record performance metrics
                execution_time_ms = (time.time() - start_time) * 1000
                if debugger and execution_time_ms > 100:  # Log slow operations
                    perf_event = DebugEvent(
                        event_type=EventType.PERFORMANCE_WARNING,
                        severity=Severity.MEDIUM,
                        message=f"Slow {method_name} execution: {execution_time_ms:.1f}ms",
                        data={
                            'method': method_name,
                            'execution_time_ms': execution_time_ms
                        }
                    )
                    debugger.event_bus.emit(perf_event)
        
        return cast(F, wrapper)
    return decorator


def instrument_transaction_processing():
    """
    Decorator for transaction processing methods.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            debugger = get_debugger()
            if not debugger or not debugger.is_running:
                return func(*args, **kwargs)
            
            # Extract transaction data
            tx_data = _extract_transaction_data(args, kwargs)
            tx_hash = tx_data.get('hash', 'unknown')
            
            # Start transaction tracking
            debugger.on_transaction_start(tx_hash, tx_data)
            
            try:
                result = func(*args, **kwargs)
                
                # End transaction tracking
                result_data = _extract_transaction_result(result)
                debugger.on_transaction_end(tx_hash, result_data)
                
                return result
                
            except Exception as e:
                # Record transaction error
                error_data = {
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                debugger.on_transaction_end(tx_hash, error_data)
                raise
        
        return cast(F, wrapper)
    return decorator


def instrument_json_operations():
    """
    Decorator for JSON decode/encode operations.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            debugger = get_debugger()
            if not debugger or not debugger.is_running:
                return func(*args, **kwargs)
            
            # Get JSON validator monitor
            json_validator = debugger.monitors.get('json_validator')
            if not json_validator:
                return func(*args, **kwargs)
            
            # Extract JSON payload from arguments
            payload = _extract_json_payload(args, kwargs)
            if payload:
                # Validate the payload
                context = f"{func.__module__}.{func.__name__}"
                json_validator.validate_json_payload(payload, context)
            
            return func(*args, **kwargs)
        
        return cast(F, wrapper)
    return decorator


def instrument_cache_operations(cache_name: str):
    """
    Decorator for cache operations.
    
    Args:
        cache_name: Name of the cache being instrumented
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            debugger = get_debugger()
            if not debugger or not debugger.is_running:
                return func(*args, **kwargs)
            
            # Get cache monitor
            cache_monitor = debugger.monitors.get('cache_monitor')
            if not cache_monitor:
                return func(*args, **kwargs)
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Record cache access time
                access_time_ms = (time.time() - start_time) * 1000
                cache_monitor.record_cache_access(cache_name, access_time_ms)
                
                # Track cache entry if this is a get/set operation
                if hasattr(func, '__name__'):
                    if func.__name__ in ['get', 'set', '__getitem__', '__setitem__']:
                        key = _extract_cache_key(args, kwargs)
                        if key:
                            cache_monitor.track_cache_entry(cache_name, key, result)
                
                return result
                
            except Exception as e:
                # Record cache error
                logger.warning(f"Cache operation error in {cache_name}: {e}")
                raise
        
        return cast(F, wrapper)
    return decorator


def instrument_state_operations():
    """
    Decorator for state read/write operations.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            debugger = get_debugger()
            if not debugger or not debugger.is_running:
                return func(*args, **kwargs)
            
            # Get determinism validator
            det_validator = debugger.monitors.get('determinism_validator')
            if not det_validator:
                return func(*args, **kwargs)
            
            # Extract state operation details
            state_key = _extract_state_key(args, kwargs)
            is_write = _is_write_operation(func.__name__)
            
            if state_key and debugger.current_transaction_hash:
                if is_write:
                    result = func(*args, **kwargs)
                    value = _extract_state_value(args, kwargs, result)
                    det_validator.record_state_access(
                        debugger.current_transaction_hash,
                        state_key,
                        True,
                        value
                    )
                    return result
                else:
                    det_validator.record_state_access(
                        debugger.current_transaction_hash,
                        state_key,
                        False
                    )
                    return func(*args, **kwargs)
            
            return func(*args, **kwargs)
        
        return cast(F, wrapper)
    return decorator


# Helper functions for extracting data from function arguments

def _extract_abci_context(method_name: str, args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Extract context information from ABCI method arguments"""
    context = {}
    
    if method_name == 'finalize_block' and args:
        # Assuming first argument is the request object
        request = args[0]
        if hasattr(request, 'height'):
            context['block_height'] = request.height
        if hasattr(request, 'txs'):
            context['transaction_count'] = len(request.txs)
    
    elif method_name == 'commit' and args:
        # Extract from commit arguments
        if len(args) > 0 and hasattr(args[0], 'height'):
            context['block_height'] = args[0].height
    
    return context


def _extract_app_hash_from_result(result: Any) -> str:
    """Extract app hash from method result"""
    if hasattr(result, 'app_hash'):
        return result.app_hash.hex() if hasattr(result.app_hash, 'hex') else str(result.app_hash)
    return ''


def _extract_transaction_data(args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Extract transaction data from arguments"""
    tx_data = {}
    
    # Try to extract from first argument (common pattern)
    if args and hasattr(args[0], '__dict__'):
        tx_obj = args[0]
        if hasattr(tx_obj, 'hash'):
            tx_data['hash'] = tx_obj.hash
        if hasattr(tx_obj, 'payload'):
            tx_data['payload'] = tx_obj.payload
        if hasattr(tx_obj, 'sender'):
            tx_data['sender'] = tx_obj.sender
    
    # Try to extract from kwargs
    for key in ['hash', 'payload', 'sender', 'contract', 'method']:
        if key in kwargs:
            tx_data[key] = kwargs[key]
    
    return tx_data


def _extract_transaction_result(result: Any) -> Dict[str, Any]:
    """Extract transaction result data"""
    result_data = {}
    
    if hasattr(result, '__dict__'):
        result_data.update(result.__dict__)
    elif isinstance(result, dict):
        result_data.update(result)
    else:
        result_data['result'] = str(result)
    
    return result_data


def _extract_json_payload(args: tuple, kwargs: dict) -> Optional[str]:
    """Extract JSON payload from function arguments"""
    # Look for string arguments that might be JSON
    for arg in args:
        if isinstance(arg, str) and len(arg) > 0:
            # Simple heuristic: starts with { or [
            if arg.strip().startswith(('{', '[')):
                return arg
    
    # Check kwargs for common JSON parameter names
    for key in ['json', 'payload', 'data', 'content']:
        if key in kwargs and isinstance(kwargs[key], str):
            return kwargs[key]
    
    return None


def _extract_cache_key(args: tuple, kwargs: dict) -> Optional[str]:
    """Extract cache key from function arguments"""
    # First argument is usually the key
    if args and isinstance(args[0], (str, int)):
        return str(args[0])
    
    # Check kwargs
    if 'key' in kwargs:
        return str(kwargs['key'])
    
    return None


def _extract_state_key(args: tuple, kwargs: dict) -> Optional[str]:
    """Extract state key from function arguments"""
    # Similar to cache key extraction
    if args and isinstance(args[0], (str, int)):
        return str(args[0])
    
    for key_name in ['key', 'state_key', 'name']:
        if key_name in kwargs:
            return str(kwargs[key_name])
    
    return None


def _is_write_operation(func_name: str) -> bool:
    """Determine if function is a write operation based on name"""
    write_patterns = ['set', 'put', 'write', 'store', 'save', 'update', 'delete', 'remove']
    return any(pattern in func_name.lower() for pattern in write_patterns)


def _extract_state_value(args: tuple, kwargs: dict, result: Any) -> Any:
    """Extract state value from arguments or result"""
    # For set operations, value is usually second argument
    if len(args) > 1:
        return args[1]
    
    # Check kwargs
    if 'value' in kwargs:
        return kwargs['value']
    
    # Return result if nothing else found
    return result


# Context manager for manual instrumentation

class DebuggerContext:
    """Context manager for manual debugger instrumentation"""
    
    def __init__(self, operation_name: str, **context_data):
        self.operation_name = operation_name
        self.context_data = context_data
        self.start_time = None
        self.debugger = None
    
    def __enter__(self):
        self.debugger = get_debugger()
        if self.debugger and self.debugger.is_running:
            self.start_time = time.time()
            
            # Set context if provided
            if 'block_height' in self.context_data or 'transaction_hash' in self.context_data:
                self.debugger.set_context(
                    block_height=self.context_data.get('block_height'),
                    transaction_hash=self.context_data.get('transaction_hash')
                )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.debugger and self.debugger.is_running and self.start_time:
            execution_time_ms = (time.time() - self.start_time) * 1000
            
            if exc_type:
                # Error occurred
                error_event = DebugEvent(
                    event_type=EventType.TRANSACTION_ERROR,
                    severity=Severity.HIGH,
                    message=f"Error in {self.operation_name}: {str(exc_val)}",
                    data={
                        'operation': self.operation_name,
                        'error': str(exc_val),
                        'error_type': exc_type.__name__,
                        'execution_time_ms': execution_time_ms,
                        **self.context_data
                    }
                )
                self.debugger.event_bus.emit(error_event)
            
            elif execution_time_ms > 100:  # Log slow operations
                perf_event = DebugEvent(
                    event_type=EventType.PERFORMANCE_WARNING,
                    severity=Severity.MEDIUM,
                    message=f"Slow operation {self.operation_name}: {execution_time_ms:.1f}ms",
                    data={
                        'operation': self.operation_name,
                        'execution_time_ms': execution_time_ms,
                        **self.context_data
                    }
                )
                self.debugger.event_bus.emit(perf_event)
    
    def emit_event(self, event_type: EventType, severity: Severity, message: str, **data):
        """Emit a custom event within this context"""
        if self.debugger and self.debugger.is_running:
            event = DebugEvent(
                event_type=event_type,
                severity=severity,
                message=message,
                data={**self.context_data, **data}
            )
            self.debugger.event_bus.emit(event)