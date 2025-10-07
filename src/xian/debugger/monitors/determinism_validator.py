"""
Determinism Validator Monitor

Monitors contract execution for non-deterministic behavior that could lead
to state divergence between nodes.
"""

import hashlib
import random
import time
import os
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger

from .base import EventDrivenMonitor
from ..core.config import DebuggerConfig
from ..core.events import (
    EventBus, DebugEvent, EventType, Severity
)


class ExecutionTrace:
    """Represents an execution trace for determinism analysis"""
    
    def __init__(self, transaction_hash: str, contract_name: str, method_name: str):
        self.transaction_hash = transaction_hash
        self.contract_name = contract_name
        self.method_name = method_name
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        
        # Execution details
        self.random_calls: List[Dict[str, Any]] = []
        self.time_calls: List[Dict[str, Any]] = []
        self.io_operations: List[Dict[str, Any]] = []
        self.external_calls: List[Dict[str, Any]] = []
        
        # State changes
        self.state_reads: List[str] = []
        self.state_writes: List[Tuple[str, Any]] = []
        
        # Result
        self.result: Optional[Any] = None
        self.result_hash: Optional[str] = None
        self.gas_used: Optional[int] = None
        
        # Determinism flags
        self.is_deterministic = True
        self.non_deterministic_reasons: List[str] = []
    
    def add_random_call(self, function_name: str, args: List[Any], result: Any):
        """Record a random function call"""
        self.random_calls.append({
            'function': function_name,
            'args': args,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        self.is_deterministic = False
        self.non_deterministic_reasons.append(f"Random call: {function_name}")
    
    def add_time_call(self, function_name: str, result: Any):
        """Record a time-related function call"""
        self.time_calls.append({
            'function': function_name,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        self.is_deterministic = False
        self.non_deterministic_reasons.append(f"Time call: {function_name}")
    
    def add_io_operation(self, operation_type: str, details: Dict[str, Any]):
        """Record an I/O operation"""
        self.io_operations.append({
            'type': operation_type,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        self.is_deterministic = False
        self.non_deterministic_reasons.append(f"I/O operation: {operation_type}")
    
    def add_external_call(self, target: str, method: str, args: List[Any], result: Any):
        """Record an external call"""
        self.external_calls.append({
            'target': target,
            'method': method,
            'args': args,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        # External calls might be non-deterministic depending on implementation
    
    def add_state_read(self, key: str):
        """Record a state read operation"""
        self.state_reads.append(key)
    
    def add_state_write(self, key: str, value: Any):
        """Record a state write operation"""
        self.state_writes.append((key, value))
    
    def finalize(self, result: Any, gas_used: Optional[int] = None):
        """Finalize the execution trace"""
        self.end_time = datetime.now()
        self.result = result
        self.gas_used = gas_used
        
        # Generate result hash for comparison
        if result is not None:
            result_str = str(result)
            self.result_hash = hashlib.sha256(result_str.encode()).hexdigest()
    
    def get_execution_time_ms(self) -> float:
        """Get execution time in milliseconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary"""
        return {
            'transaction_hash': self.transaction_hash,
            'contract_name': self.contract_name,
            'method_name': self.method_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'execution_time_ms': self.get_execution_time_ms(),
            'is_deterministic': self.is_deterministic,
            'non_deterministic_reasons': self.non_deterministic_reasons,
            'random_calls_count': len(self.random_calls),
            'time_calls_count': len(self.time_calls),
            'io_operations_count': len(self.io_operations),
            'external_calls_count': len(self.external_calls),
            'state_reads_count': len(self.state_reads),
            'state_writes_count': len(self.state_writes),
            'result_hash': self.result_hash,
            'gas_used': self.gas_used
        }


class DeterminismValidator(EventDrivenMonitor):
    """
    Monitors contract execution for non-deterministic behavior.
    
    This monitor tracks function calls, state access patterns, and execution
    results to detect non-deterministic behavior that could cause divergence.
    """
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        super().__init__(config, event_bus)
        
        # Execution tracking
        self.active_traces: Dict[str, ExecutionTrace] = {}  # tx_hash -> trace
        self.completed_traces: List[ExecutionTrace] = []
        self.max_completed_traces = 1000
        
        # Determinism analysis
        self.execution_patterns: Dict[str, List[str]] = defaultdict(list)  # contract.method -> result_hashes
        self.non_deterministic_contracts: Set[str] = set()
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)
        
        # Random seed tracking
        self.random_seeds: Dict[str, Any] = {}  # tx_hash -> seed
        self.seed_mismatches: List[Dict[str, Any]] = []
        
        # Time consistency tracking
        self.block_timestamps: Dict[int, datetime] = {}
        self.timestamp_inconsistencies: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.execution_times: Dict[str, List[float]] = defaultdict(list)  # contract.method -> times
        self.gas_usage: Dict[str, List[int]] = defaultdict(list)  # contract.method -> gas amounts
        
        # Statistics
        self.total_executions = 0
        self.non_deterministic_executions = 0
        self.random_calls_detected = 0
        self.time_calls_detected = 0
        self.io_operations_detected = 0
    
    def initialize(self) -> bool:
        """Initialize the determinism validator"""
        logger.info("Initializing Determinism Validator")
        
        # Load configuration
        if 'determinism_validator' in self.config.custom_settings:
            settings = self.config.custom_settings['determinism_validator']
            self.max_completed_traces = settings.get('max_completed_traces', self.max_completed_traces)
        
        return True
    
    def register_event_handlers(self):
        """Register event handlers"""
        self.event_bus.subscribe(EventType.TRANSACTION_START, self._on_transaction_start)
        self.event_bus.subscribe(EventType.TRANSACTION_END, self._on_transaction_end)
        self.event_bus.subscribe(EventType.BLOCK_START, self._on_block_start)
    
    def unregister_event_handlers(self):
        """Unregister event handlers"""
        self.event_bus.unsubscribe(EventType.TRANSACTION_START, self._on_transaction_start)
        self.event_bus.unsubscribe(EventType.TRANSACTION_END, self._on_transaction_end)
        self.event_bus.unsubscribe(EventType.BLOCK_START, self._on_block_start)
    
    def _on_transaction_start(self, event: DebugEvent):
        """Handle transaction start"""
        if not event.transaction_hash:
            return
        
        # Extract contract and method information
        contract_name = event.data.get('contract', 'unknown')
        method_name = event.data.get('method', 'unknown')
        
        # Create execution trace
        trace = ExecutionTrace(event.transaction_hash, contract_name, method_name)
        self.active_traces[event.transaction_hash] = trace
        
        # Track random seed if provided
        if 'random_seed' in event.data:
            self.random_seeds[event.transaction_hash] = event.data['random_seed']
    
    def _on_transaction_end(self, event: DebugEvent):
        """Handle transaction end"""
        if not event.transaction_hash:
            return
        
        trace = self.active_traces.get(event.transaction_hash)
        if not trace:
            return
        
        # Finalize trace
        result = event.data.get('result')
        gas_used = event.data.get('gas_used')
        trace.finalize(result, gas_used)
        
        # Analyze trace
        self._analyze_execution_trace(trace)
        
        # Move to completed traces
        self.completed_traces.append(trace)
        if len(self.completed_traces) > self.max_completed_traces:
            self.completed_traces.pop(0)
        
        # Remove from active traces
        del self.active_traces[event.transaction_hash]
        
        self.total_executions += 1
    
    def _on_block_start(self, event: DebugEvent):
        """Handle block start to track timestamps"""
        if event.block_height:
            self.block_timestamps[event.block_height] = datetime.now()
            
            # Check for timestamp consistency
            self._check_timestamp_consistency(event.block_height, event.data)
    
    def _analyze_execution_trace(self, trace: ExecutionTrace):
        """Analyze an execution trace for determinism issues"""
        contract_method = f"{trace.contract_name}.{trace.method_name}"
        
        # Check if execution was non-deterministic
        if not trace.is_deterministic:
            self.non_deterministic_executions += 1
            self.non_deterministic_contracts.add(trace.contract_name)
            
            # Emit non-deterministic behavior event
            non_det_event = DebugEvent(
                event_type=EventType.NON_DETERMINISTIC_BEHAVIOR,
                severity=Severity.HIGH,
                message=f"Non-deterministic execution in {contract_method}",
                transaction_hash=trace.transaction_hash,
                data={
                    'contract_name': trace.contract_name,
                    'method_name': trace.method_name,
                    'reasons': trace.non_deterministic_reasons,
                    'trace_summary': trace.to_dict()
                }
            )
            self.emit_event(non_det_event)
        
        # Track execution patterns
        if trace.result_hash:
            self.execution_patterns[contract_method].append(trace.result_hash)
            
            # Check for result inconsistencies
            self._check_result_consistency(contract_method, trace)
        
        # Track performance metrics
        execution_time = trace.get_execution_time_ms()
        self.execution_times[contract_method].append(execution_time)
        
        if trace.gas_used:
            self.gas_usage[contract_method].append(trace.gas_used)
        
        # Update statistics
        self.random_calls_detected += len(trace.random_calls)
        self.time_calls_detected += len(trace.time_calls)
        self.io_operations_detected += len(trace.io_operations)
    
    def _check_result_consistency(self, contract_method: str, trace: ExecutionTrace):
        """Check for result consistency across executions"""
        result_hashes = self.execution_patterns[contract_method]
        
        # If we have multiple executions, check for consistency
        if len(result_hashes) > 1:
            unique_hashes = set(result_hashes[-10:])  # Check last 10 executions
            
            if len(unique_hashes) > 1:
                # Multiple different results for same contract method
                inconsistency_event = DebugEvent(
                    event_type=EventType.NON_DETERMINISTIC_BEHAVIOR,
                    severity=Severity.MEDIUM,
                    message=f"Result inconsistency detected in {contract_method}",
                    transaction_hash=trace.transaction_hash,
                    data={
                        'contract_method': contract_method,
                        'unique_results': len(unique_hashes),
                        'recent_hashes': list(unique_hashes),
                        'total_executions': len(result_hashes)
                    }
                )
                self.emit_event(inconsistency_event)
    
    def _check_timestamp_consistency(self, block_height: int, block_data: Dict[str, Any]):
        """Check for timestamp consistency issues"""
        block_timestamp = block_data.get('timestamp')
        if not block_timestamp:
            return
        
        # Convert to datetime if it's a string/number
        if isinstance(block_timestamp, (int, float)):
            block_time = datetime.fromtimestamp(block_timestamp)
        elif isinstance(block_timestamp, str):
            try:
                block_time = datetime.fromisoformat(block_timestamp)
            except:
                return
        else:
            return
        
        # Check against system time
        system_time = datetime.now()
        time_diff = abs((block_time - system_time).total_seconds())
        
        # Alert if timestamp is significantly different from system time
        if time_diff > 300:  # 5 minutes threshold
            timestamp_event = DebugEvent(
                event_type=EventType.TIMESTAMP_INCONSISTENCY,
                severity=Severity.MEDIUM,
                message=f"Block timestamp inconsistency: {time_diff:.1f}s difference",
                block_height=block_height,
                data={
                    'block_timestamp': block_time.isoformat(),
                    'system_timestamp': system_time.isoformat(),
                    'difference_seconds': time_diff
                }
            )
            self.emit_event(timestamp_event)
            
            self.timestamp_inconsistencies.append({
                'block_height': block_height,
                'block_timestamp': block_time.isoformat(),
                'system_timestamp': system_time.isoformat(),
                'difference_seconds': time_diff
            })
    
    # Public API for instrumentation
    def start_execution_trace(self, transaction_hash: str, contract_name: str, method_name: str):
        """Start tracking execution for determinism analysis"""
        if transaction_hash not in self.active_traces:
            trace = ExecutionTrace(transaction_hash, contract_name, method_name)
            self.active_traces[transaction_hash] = trace
        return self.active_traces[transaction_hash]
    
    def record_random_call(self, transaction_hash: str, function_name: str, args: List[Any], result: Any):
        """Record a random function call"""
        trace = self.active_traces.get(transaction_hash)
        if trace:
            trace.add_random_call(function_name, args, result)
    
    def record_time_call(self, transaction_hash: str, function_name: str, result: Any):
        """Record a time-related function call"""
        trace = self.active_traces.get(transaction_hash)
        if trace:
            trace.add_time_call(function_name, result)
    
    def record_io_operation(self, transaction_hash: str, operation_type: str, details: Dict[str, Any]):
        """Record an I/O operation"""
        trace = self.active_traces.get(transaction_hash)
        if trace:
            trace.add_io_operation(operation_type, details)
    
    def record_state_access(self, transaction_hash: str, key: str, is_write: bool, value: Any = None):
        """Record state access"""
        trace = self.active_traces.get(transaction_hash)
        if trace:
            if is_write:
                trace.add_state_write(key, value)
            else:
                trace.add_state_read(key)
    
    def check_random_seed_consistency(self, transaction_hash: str, expected_seed: Any):
        """Check if random seed matches expected value"""
        actual_seed = self.random_seeds.get(transaction_hash)
        
        if actual_seed is not None and actual_seed != expected_seed:
            mismatch = {
                'transaction_hash': transaction_hash,
                'expected_seed': expected_seed,
                'actual_seed': actual_seed,
                'timestamp': datetime.now().isoformat()
            }
            self.seed_mismatches.append(mismatch)
            
            seed_event = DebugEvent(
                event_type=EventType.RANDOM_SEED_MISMATCH,
                severity=Severity.HIGH,
                message=f"Random seed mismatch in transaction {transaction_hash[:16]}...",
                transaction_hash=transaction_hash,
                data=mismatch
            )
            self.emit_event(seed_event)
    
    def get_determinism_stats(self) -> Dict[str, Any]:
        """Get determinism validation statistics"""
        non_det_rate = self.non_deterministic_executions / max(1, self.total_executions)
        
        # Get most problematic contracts
        contract_issues = {}
        for contract in self.non_deterministic_contracts:
            issues = sum(1 for trace in self.completed_traces 
                        if trace.contract_name == contract and not trace.is_deterministic)
            contract_issues[contract] = issues
        
        top_problematic = sorted(contract_issues.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Calculate average execution times
        avg_execution_times = {}
        for contract_method, times in self.execution_times.items():
            if times:
                avg_execution_times[contract_method] = sum(times) / len(times)
        
        return {
            'total_executions': self.total_executions,
            'non_deterministic_executions': self.non_deterministic_executions,
            'non_deterministic_rate': non_det_rate,
            'non_deterministic_contracts_count': len(self.non_deterministic_contracts),
            'random_calls_detected': self.random_calls_detected,
            'time_calls_detected': self.time_calls_detected,
            'io_operations_detected': self.io_operations_detected,
            'seed_mismatches': len(self.seed_mismatches),
            'timestamp_inconsistencies': len(self.timestamp_inconsistencies),
            'top_problematic_contracts': top_problematic,
            'active_traces': len(self.active_traces),
            'completed_traces': len(self.completed_traces),
            'tracked_contract_methods': len(self.execution_patterns)
        }
    
    def get_contract_analysis(self, contract_name: str) -> Dict[str, Any]:
        """Get detailed analysis for a specific contract"""
        contract_traces = [
            trace for trace in self.completed_traces
            if trace.contract_name == contract_name
        ]
        
        if not contract_traces:
            return {'error': f'No traces found for contract {contract_name}'}
        
        total_traces = len(contract_traces)
        non_det_traces = [trace for trace in contract_traces if not trace.is_deterministic]
        
        # Analyze methods
        method_stats = defaultdict(lambda: {'executions': 0, 'non_deterministic': 0, 'avg_time_ms': 0})
        
        for trace in contract_traces:
            method = trace.method_name
            method_stats[method]['executions'] += 1
            if not trace.is_deterministic:
                method_stats[method]['non_deterministic'] += 1
            method_stats[method]['avg_time_ms'] += trace.get_execution_time_ms()
        
        # Calculate averages
        for method, stats in method_stats.items():
            stats['avg_time_ms'] /= stats['executions']
            stats['non_deterministic_rate'] = stats['non_deterministic'] / stats['executions']
        
        return {
            'contract_name': contract_name,
            'total_executions': total_traces,
            'non_deterministic_executions': len(non_det_traces),
            'non_deterministic_rate': len(non_det_traces) / total_traces,
            'method_statistics': dict(method_stats),
            'common_non_deterministic_reasons': self._get_common_reasons(non_det_traces)
        }
    
    def _get_common_reasons(self, traces: List[ExecutionTrace]) -> Dict[str, int]:
        """Get common non-deterministic reasons from traces"""
        reason_counts = defaultdict(int)
        
        for trace in traces:
            for reason in trace.non_deterministic_reasons:
                reason_counts[reason] += 1
        
        return dict(sorted(reason_counts.items(), key=lambda x: x[1], reverse=True))
    
    def get_recent_non_deterministic_executions(self, count: int = 20) -> List[Dict[str, Any]]:
        """Get recent non-deterministic executions"""
        non_det_traces = [
            trace for trace in self.completed_traces
            if not trace.is_deterministic
        ][-count:]
        
        return [trace.to_dict() for trace in non_det_traces]