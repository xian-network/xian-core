"""
Event System for State Divergence Debugger

Defines events and event handling for the debugging system.
"""

import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime


class EventType(Enum):
    """Types of debug events"""
    # State-related events
    STATE_DIVERGENCE = "state_divergence"
    STATE_SNAPSHOT = "state_snapshot"
    STATE_COMPARISON = "state_comparison"
    
    # Cache-related events
    CACHE_LEAK = "cache_leak"
    CACHE_POLLUTION = "cache_pollution"
    CACHE_CLEANUP_FAILURE = "cache_cleanup_failure"
    
    # JSON/Decode events
    JSON_DECODE_FAILURE = "json_decode_failure"
    JSON_VALIDATION_ERROR = "json_validation_error"
    PAYLOAD_CORRUPTION = "payload_corruption"
    
    # Transaction events
    TRANSACTION_START = "transaction_start"
    TRANSACTION_END = "transaction_end"
    TRANSACTION_ERROR = "transaction_error"
    
    # Block events
    BLOCK_START = "block_start"
    BLOCK_END = "block_end"
    BLOCK_COMMIT = "block_commit"
    
    # Determinism events
    NON_DETERMINISTIC_BEHAVIOR = "non_deterministic_behavior"
    RANDOM_SEED_MISMATCH = "random_seed_mismatch"
    TIMESTAMP_INCONSISTENCY = "timestamp_inconsistency"
    
    # System events
    DEBUGGER_START = "debugger_start"
    DEBUGGER_STOP = "debugger_stop"
    PERFORMANCE_WARNING = "performance_warning"
    MEMORY_THRESHOLD_EXCEEDED = "memory_threshold_exceeded"
    
    # Alert events
    CRITICAL_ALERT = "critical_alert"
    WARNING_ALERT = "warning_alert"
    INFO_ALERT = "info_alert"
    
    # Operation events
    OPERATION_START = "operation_start"
    OPERATION_END = "operation_end"
    
    # Custom/Generic events
    CUSTOM = "custom"


class Severity(Enum):
    """Event severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class DebugEvent:
    """A debug event with metadata and payload"""
    
    event_type: EventType
    severity: Severity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Context information
    block_height: Optional[int] = None
    transaction_hash: Optional[str] = None
    node_id: Optional[str] = None
    
    # Event-specific data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    processing_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    
    # Related events
    related_events: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization processing"""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'block_height': self.block_height,
            'transaction_hash': self.transaction_hash,
            'node_id': self.node_id,
            'data': self.data,
            'processing_time_ms': self.processing_time_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'related_events': self.related_events
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DebugEvent':
        """Create event from dictionary"""
        return cls(
            event_type=EventType(data['event_type']),
            severity=Severity(data['severity']),
            message=data['message'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            event_id=data.get('event_id', str(uuid.uuid4())),
            block_height=data.get('block_height'),
            transaction_hash=data.get('transaction_hash'),
            node_id=data.get('node_id'),
            data=data.get('data', {}),
            processing_time_ms=data.get('processing_time_ms'),
            memory_usage_mb=data.get('memory_usage_mb'),
            related_events=data.get('related_events', [])
        )
    
    def add_related_event(self, event_id: str):
        """Add a related event ID"""
        if event_id not in self.related_events:
            self.related_events.append(event_id)
    
    def is_critical(self) -> bool:
        """Check if event is critical severity"""
        return self.severity == Severity.CRITICAL
    
    def is_state_related(self) -> bool:
        """Check if event is related to state management"""
        state_events = {
            EventType.STATE_DIVERGENCE,
            EventType.STATE_SNAPSHOT,
            EventType.STATE_COMPARISON,
            EventType.CACHE_LEAK,
            EventType.CACHE_POLLUTION
        }
        return self.event_type in state_events


class EventHandler:
    """Base class for event handlers"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    def handle(self, event: DebugEvent) -> bool:
        """Handle an event. Return True if handled successfully."""
        raise NotImplementedError
    
    def can_handle(self, event: DebugEvent) -> bool:
        """Check if this handler can process the given event"""
        return self.enabled


class EventBus:
    """Event bus for managing debug events"""
    
    def __init__(self):
        self.handlers: List[EventHandler] = []
        self.event_history: List[DebugEvent] = []
        self.max_history_size = 10000
        self._subscribers: Dict[EventType, List[Callable]] = {}
    
    def register_handler(self, handler: EventHandler):
        """Register an event handler"""
        self.handlers.append(handler)
    
    def unregister_handler(self, handler: EventHandler):
        """Unregister an event handler"""
        if handler in self.handlers:
            self.handlers.remove(handler)
    
    def subscribe(self, event_type: EventType, callback: Callable[[DebugEvent], None]):
        """Subscribe to specific event types"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[DebugEvent], None]):
        """Unsubscribe from event type"""
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
    
    def emit(self, event: DebugEvent):
        """Emit an event to all handlers and subscribers"""
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
        
        # Process handlers
        for handler in self.handlers:
            if handler.can_handle(event):
                try:
                    handler.handle(event)
                except Exception as e:
                    # Create error event for handler failure
                    error_event = DebugEvent(
                        event_type=EventType.DEBUGGER_STOP,
                        severity=Severity.HIGH,
                        message=f"Handler {handler.name} failed: {str(e)}",
                        data={'original_event_id': event.event_id, 'error': str(e)}
                    )
                    self.event_history.append(error_event)
        
        # Notify subscribers
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    # Log subscriber error but don't create recursive events
                    pass
    
    def get_events(self, 
                   event_type: Optional[EventType] = None,
                   severity: Optional[Severity] = None,
                   since: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[DebugEvent]:
        """Get events matching criteria"""
        events = self.event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        if limit:
            events = events[-limit:]
        
        return events
    
    def get_critical_events(self, limit: int = 100) -> List[DebugEvent]:
        """Get recent critical events"""
        return self.get_events(severity=Severity.CRITICAL, limit=limit)
    
    def clear_history(self):
        """Clear event history"""
        self.event_history.clear()


# Convenience functions for creating common events
def create_state_divergence_event(message: str, block_height: int, 
                                 expected_hash: str, actual_hash: str,
                                 node_id: Optional[str] = None) -> DebugEvent:
    """Create a state divergence event"""
    return DebugEvent(
        event_type=EventType.STATE_DIVERGENCE,
        severity=Severity.CRITICAL,
        message=message,
        block_height=block_height,
        node_id=node_id,
        data={
            'expected_hash': expected_hash,
            'actual_hash': actual_hash,
            'hash_mismatch': True
        }
    )


def create_cache_leak_event(message: str, leaked_keys: List[str],
                           transaction_hash: Optional[str] = None) -> DebugEvent:
    """Create a cache leak event"""
    return DebugEvent(
        event_type=EventType.CACHE_LEAK,
        severity=Severity.HIGH,
        message=message,
        transaction_hash=transaction_hash,
        data={
            'leaked_keys': leaked_keys,
            'leak_count': len(leaked_keys)
        }
    )


def create_json_decode_error_event(message: str, payload: str,
                                  error: str, transaction_hash: Optional[str] = None) -> DebugEvent:
    """Create a JSON decode error event"""
    return DebugEvent(
        event_type=EventType.JSON_DECODE_FAILURE,
        severity=Severity.HIGH,
        message=message,
        transaction_hash=transaction_hash,
        data={
            'payload': payload[:1000],  # Truncate large payloads
            'error': error,
            'payload_length': len(payload)
        }
    )


def create_performance_warning_event(message: str, metric: str, 
                                    value: float, threshold: float) -> DebugEvent:
    """Create a performance warning event"""
    return DebugEvent(
        event_type=EventType.PERFORMANCE_WARNING,
        severity=Severity.MEDIUM,
        message=message,
        data={
            'metric': metric,
            'value': value,
            'threshold': threshold,
            'exceeded_by': value - threshold
        }
    )