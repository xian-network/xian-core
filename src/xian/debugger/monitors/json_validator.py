"""
JSON Validator Monitor

Monitors JSON decode operations and detects silent failures, validation errors,
and payload corruption that could lead to state divergence.
"""

import json
import hashlib
import re
from typing import Dict, Any, Optional, List, Set, Union
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger

from .base import EventDrivenMonitor
from ..core.config import DebuggerConfig
from ..core.events import (
    EventBus, DebugEvent, EventType, Severity,
    create_json_decode_error_event
)


class JsonValidationResult:
    """Result of JSON validation"""
    
    def __init__(self, is_valid: bool, payload: str, error: Optional[str] = None):
        self.is_valid = is_valid
        self.payload = payload
        self.error = error
        self.timestamp = datetime.now()
        self.payload_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]
        self.payload_size = len(payload)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'error': self.error,
            'timestamp': self.timestamp.isoformat(),
            'payload_hash': self.payload_hash,
            'payload_size': self.payload_size,
            'payload_preview': self.payload[:200] if self.payload else None
        }


class JsonValidator(EventDrivenMonitor):
    """
    Monitors JSON operations and validates payloads.
    
    This monitor intercepts JSON decode operations, validates payloads,
    detects silent failures, and identifies corruption patterns.
    """
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        super().__init__(config, event_bus)
        
        # Validation tracking
        self.validation_results: List[JsonValidationResult] = []
        self.max_results = 10000
        
        # Error patterns
        self.error_patterns: Dict[str, int] = defaultdict(int)
        self.suspicious_patterns: Set[str] = {
            r'null',  # Unexpected null values
            r'undefined',  # JavaScript-style undefined
            r'NaN',  # Not a Number
            r'Infinity',  # Infinity values
            r'\\u0000',  # Null bytes
            r'\\x[0-9a-fA-F]{2}',  # Hex escape sequences
        }
        
        # Payload analysis
        self.payload_hashes: Dict[str, int] = defaultdict(int)  # Track duplicate payloads
        self.payload_sizes: List[int] = []
        self.max_payload_size = 1024 * 1024  # 1MB
        
        # Schema validation
        self.expected_schemas: Dict[str, Dict[str, Any]] = {}
        self.schema_violations: Dict[str, int] = defaultdict(int)
        
        # Performance tracking
        self.decode_times: List[float] = []
        self.slow_decode_threshold_ms = 50.0
        
        # Statistics
        self.total_validations = 0
        self.failed_validations = 0
        self.silent_failures_detected = 0
        self.corruption_events_detected = 0
    
    def initialize(self) -> bool:
        """Initialize the JSON validator"""
        logger.info("Initializing JSON Validator")
        
        # Load configuration
        if 'json_validator' in self.config.custom_settings:
            settings = self.config.custom_settings['json_validator']
            self.max_payload_size = settings.get('max_payload_size', self.max_payload_size)
            self.slow_decode_threshold_ms = settings.get('slow_decode_threshold_ms', self.slow_decode_threshold_ms)
            
            # Load custom suspicious patterns
            custom_patterns = settings.get('suspicious_patterns', [])
            self.suspicious_patterns.update(custom_patterns)
        
        return True
    
    def register_event_handlers(self):
        """Register event handlers"""
        # We'll hook into transaction events to validate JSON payloads
        self.event_bus.subscribe(EventType.TRANSACTION_START, self._on_transaction_start)
        self.event_bus.subscribe(EventType.TRANSACTION_END, self._on_transaction_end)
    
    def unregister_event_handlers(self):
        """Unregister event handlers"""
        self.event_bus.unsubscribe(EventType.TRANSACTION_START, self._on_transaction_start)
        self.event_bus.unsubscribe(EventType.TRANSACTION_END, self._on_transaction_end)
    
    def _on_transaction_start(self, event: DebugEvent):
        """Validate JSON in transaction start data"""
        if 'payload' in event.data:
            payload = event.data['payload']
            if isinstance(payload, str):
                self.validate_json_payload(payload, f"tx_start_{event.transaction_hash}")
    
    def _on_transaction_end(self, event: DebugEvent):
        """Validate JSON in transaction end data"""
        if 'result' in event.data:
            result = event.data['result']
            if isinstance(result, str):
                self.validate_json_payload(result, f"tx_end_{event.transaction_hash}")
    
    def validate_json_payload(self, payload: str, context: str = "unknown") -> JsonValidationResult:
        """
        Validate a JSON payload and detect issues.
        
        Args:
            payload: JSON string to validate
            context: Context information for debugging
            
        Returns:
            JsonValidationResult: Validation result
        """
        import time
        start_time = time.time()
        
        try:
            self.total_validations += 1
            
            # Basic size check
            if len(payload) > self.max_payload_size:
                result = JsonValidationResult(
                    False, payload, f"Payload too large: {len(payload)} bytes"
                )
                self._handle_validation_result(result, context)
                return result
            
            # Check for suspicious patterns
            suspicious_findings = self._check_suspicious_patterns(payload)
            if suspicious_findings:
                result = JsonValidationResult(
                    False, payload, f"Suspicious patterns found: {suspicious_findings}"
                )
                self._handle_validation_result(result, context)
                return result
            
            # Attempt JSON decode
            try:
                decoded = json.loads(payload)
                
                # Validate structure if schema is available
                schema_errors = self._validate_against_schema(decoded, context)
                if schema_errors:
                    result = JsonValidationResult(
                        False, payload, f"Schema validation failed: {schema_errors}"
                    )
                    self._handle_validation_result(result, context)
                    return result
                
                # Check for silent corruption
                corruption_issues = self._check_for_corruption(decoded, payload)
                if corruption_issues:
                    result = JsonValidationResult(
                        False, payload, f"Corruption detected: {corruption_issues}"
                    )
                    self._handle_validation_result(result, context)
                    return result
                
                # Successful validation
                result = JsonValidationResult(True, payload)
                self._handle_validation_result(result, context)
                return result
                
            except json.JSONDecodeError as e:
                self.failed_validations += 1
                result = JsonValidationResult(
                    False, payload, f"JSON decode error: {str(e)}"
                )
                self._handle_validation_result(result, context)
                return result
            
        except Exception as e:
            # Unexpected error in validation
            result = JsonValidationResult(
                False, payload, f"Validation error: {str(e)}"
            )
            self._handle_validation_result(result, context)
            return result
        
        finally:
            # Track decode time
            decode_time_ms = (time.time() - start_time) * 1000
            self.decode_times.append(decode_time_ms)
            
            if decode_time_ms > self.slow_decode_threshold_ms:
                perf_event = DebugEvent(
                    event_type=EventType.PERFORMANCE_WARNING,
                    severity=Severity.MEDIUM,
                    message=f"Slow JSON decode: {decode_time_ms:.1f}ms",
                    data={
                        'decode_time_ms': decode_time_ms,
                        'threshold_ms': self.slow_decode_threshold_ms,
                        'payload_size': len(payload),
                        'context': context
                    }
                )
                self.emit_event(perf_event)
    
    def _check_suspicious_patterns(self, payload: str) -> List[str]:
        """Check for suspicious patterns in payload"""
        findings = []
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, payload):
                findings.append(pattern)
        
        return findings
    
    def _validate_against_schema(self, decoded: Any, context: str) -> Optional[str]:
        """Validate decoded JSON against expected schema"""
        if context not in self.expected_schemas:
            return None
        
        expected_schema = self.expected_schemas[context]
        
        try:
            # Simple schema validation (can be extended with jsonschema library)
            if isinstance(expected_schema, dict) and isinstance(decoded, dict):
                # Check required fields
                required_fields = expected_schema.get('required', [])
                for field in required_fields:
                    if field not in decoded:
                        self.schema_violations[context] += 1
                        return f"Missing required field: {field}"
                
                # Check field types
                field_types = expected_schema.get('properties', {})
                for field, expected_type in field_types.items():
                    if field in decoded:
                        actual_type = type(decoded[field]).__name__
                        if actual_type != expected_type:
                            self.schema_violations[context] += 1
                            return f"Type mismatch for {field}: expected {expected_type}, got {actual_type}"
            
            return None
            
        except Exception as e:
            return f"Schema validation error: {str(e)}"
    
    def _check_for_corruption(self, decoded: Any, original_payload: str) -> Optional[str]:
        """Check for signs of data corruption"""
        try:
            # Re-encode and compare
            re_encoded = json.dumps(decoded, sort_keys=True, separators=(',', ':'))
            original_normalized = json.dumps(json.loads(original_payload), sort_keys=True, separators=(',', ':'))
            
            if re_encoded != original_normalized:
                self.corruption_events_detected += 1
                return "Round-trip encoding mismatch"
            
            # Check for unusual values
            corruption_signs = self._find_corruption_signs(decoded)
            if corruption_signs:
                self.corruption_events_detected += 1
                return f"Corruption signs: {corruption_signs}"
            
            return None
            
        except Exception as e:
            return f"Corruption check failed: {str(e)}"
    
    def _find_corruption_signs(self, obj: Any, path: str = "") -> List[str]:
        """Recursively find signs of corruption in decoded object"""
        signs = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                
                # Check for suspicious keys
                if not isinstance(key, str) or not key.strip():
                    signs.append(f"Invalid key at {new_path}")
                
                # Recurse into value
                signs.extend(self._find_corruption_signs(value, new_path))
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                signs.extend(self._find_corruption_signs(item, new_path))
        
        elif isinstance(obj, str):
            # Check for suspicious string values
            if '\x00' in obj:  # Null bytes
                signs.append(f"Null byte in string at {path}")
            if len(obj) > 100000:  # Very long strings
                signs.append(f"Extremely long string at {path}")
        
        elif isinstance(obj, (int, float)):
            # Check for suspicious numeric values
            if isinstance(obj, float):
                if obj != obj:  # NaN check
                    signs.append(f"NaN value at {path}")
                elif obj == float('inf') or obj == float('-inf'):
                    signs.append(f"Infinity value at {path}")
        
        return signs
    
    def _handle_validation_result(self, result: JsonValidationResult, context: str):
        """Handle validation result and emit events if needed"""
        # Store result
        self.validation_results.append(result)
        if len(self.validation_results) > self.max_results:
            self.validation_results.pop(0)
        
        # Track payload hash for duplicate detection
        self.payload_hashes[result.payload_hash] += 1
        self.payload_sizes.append(result.payload_size)
        
        # Emit event for failures
        if not result.is_valid:
            # Track error pattern
            if result.error:
                self.error_patterns[result.error] += 1
            
            # Create and emit error event
            error_event = create_json_decode_error_event(
                f"JSON validation failed in {context}: {result.error}",
                result.payload,
                result.error or "Unknown error"
            )
            error_event.data.update({
                'context': context,
                'payload_hash': result.payload_hash,
                'payload_size': result.payload_size,
                'validation_result': result.to_dict()
            })
            
            self.emit_event(error_event)
        
        # Check for silent failures (duplicate payloads with different results)
        self._check_for_silent_failures(result, context)
    
    def _check_for_silent_failures(self, result: JsonValidationResult, context: str):
        """Check for silent failures by comparing with previous results"""
        # Look for previous results with same payload hash
        previous_results = [
            r for r in self.validation_results[-100:]  # Check last 100 results
            if r.payload_hash == result.payload_hash and r != result
        ]
        
        for prev_result in previous_results:
            if prev_result.is_valid != result.is_valid:
                # Same payload, different validation result - potential silent failure
                self.silent_failures_detected += 1
                
                silent_failure_event = DebugEvent(
                    event_type=EventType.JSON_DECODE_FAILURE,
                    severity=Severity.HIGH,
                    message=f"Silent JSON failure detected: same payload, different results",
                    data={
                        'context': context,
                        'payload_hash': result.payload_hash,
                        'current_result': result.to_dict(),
                        'previous_result': prev_result.to_dict(),
                        'time_diff_seconds': (result.timestamp - prev_result.timestamp).total_seconds()
                    }
                )
                
                self.emit_event(silent_failure_event)
                break
    
    # Public API methods
    def set_expected_schema(self, context: str, schema: Dict[str, Any]):
        """Set expected schema for a context"""
        self.expected_schemas[context] = schema
        logger.debug(f"Set expected schema for context: {context}")
    
    def add_suspicious_pattern(self, pattern: str):
        """Add a suspicious pattern to check for"""
        self.suspicious_patterns.add(pattern)
    
    def remove_suspicious_pattern(self, pattern: str):
        """Remove a suspicious pattern"""
        self.suspicious_patterns.discard(pattern)
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get JSON validation statistics"""
        recent_results = self.validation_results[-1000:]  # Last 1000 results
        recent_failures = [r for r in recent_results if not r.is_valid]
        
        # Calculate failure rate
        failure_rate = len(recent_failures) / max(1, len(recent_results))
        
        # Get most common errors
        top_errors = sorted(
            self.error_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Calculate average payload size
        avg_payload_size = sum(self.payload_sizes[-1000:]) / max(1, len(self.payload_sizes[-1000:]))
        
        # Calculate average decode time
        avg_decode_time_ms = sum(self.decode_times[-1000:]) / max(1, len(self.decode_times[-1000:]))
        
        return {
            'total_validations': self.total_validations,
            'failed_validations': self.failed_validations,
            'failure_rate': failure_rate,
            'silent_failures_detected': self.silent_failures_detected,
            'corruption_events_detected': self.corruption_events_detected,
            'top_error_patterns': top_errors,
            'schema_violations': dict(self.schema_violations),
            'average_payload_size': avg_payload_size,
            'average_decode_time_ms': avg_decode_time_ms,
            'suspicious_patterns_count': len(self.suspicious_patterns),
            'unique_payload_hashes': len(self.payload_hashes)
        }
    
    def get_recent_failures(self, count: int = 50) -> List[Dict[str, Any]]:
        """Get recent validation failures"""
        recent_failures = [
            r for r in self.validation_results[-count*2:]  # Get more to filter
            if not r.is_valid
        ][-count:]  # Take last N failures
        
        return [failure.to_dict() for failure in recent_failures]
    
    def clear_validation_history(self):
        """Clear validation history"""
        self.validation_results.clear()
        self.error_patterns.clear()
        self.payload_hashes.clear()
        self.payload_sizes.clear()
        self.decode_times.clear()
        logger.info("JSON validation history cleared")