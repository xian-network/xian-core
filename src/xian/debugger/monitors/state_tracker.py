"""
State Tracker Monitor

Monitors state changes and detects potential divergence issues by tracking
state snapshots, comparing app hashes, and detecting unexpected state mutations.
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from loguru import logger

from .base import EventDrivenMonitor
from ..core.config import DebuggerConfig
from ..core.events import (
    EventBus, DebugEvent, EventType, Severity,
    create_state_divergence_event
)


class StateSnapshot:
    """Represents a state snapshot at a specific point in time"""
    
    def __init__(self, block_height: int, app_hash: str, 
                 state_data: Optional[Dict[str, Any]] = None):
        self.block_height = block_height
        self.app_hash = app_hash
        self.state_data = state_data or {}
        self.timestamp = datetime.now()
        self.snapshot_id = self._generate_snapshot_id()
    
    def _generate_snapshot_id(self) -> str:
        """Generate unique snapshot ID"""
        data = f"{self.block_height}:{self.app_hash}:{self.timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary"""
        return {
            'snapshot_id': self.snapshot_id,
            'block_height': self.block_height,
            'app_hash': self.app_hash,
            'timestamp': self.timestamp.isoformat(),
            'state_data_keys': list(self.state_data.keys()) if self.state_data else [],
            'state_data_size': len(json.dumps(self.state_data)) if self.state_data else 0
        }
    
    def compare_with(self, other: 'StateSnapshot') -> Dict[str, Any]:
        """Compare this snapshot with another"""
        comparison = {
            'block_height_diff': other.block_height - self.block_height,
            'app_hash_match': self.app_hash == other.app_hash,
            'timestamp_diff_seconds': (other.timestamp - self.timestamp).total_seconds()
        }
        
        if self.state_data and other.state_data:
            # Compare state data
            self_keys = set(self.state_data.keys())
            other_keys = set(other.state_data.keys())
            
            comparison.update({
                'added_keys': list(other_keys - self_keys),
                'removed_keys': list(self_keys - other_keys),
                'common_keys': list(self_keys & other_keys),
                'modified_keys': []
            })
            
            # Check for modified values in common keys
            for key in comparison['common_keys']:
                if self.state_data[key] != other.state_data[key]:
                    comparison['modified_keys'].append(key)
        
        return comparison


class StateTracker(EventDrivenMonitor):
    """
    Monitors state changes and detects divergence issues.
    
    This monitor tracks state snapshots, compares app hashes between blocks,
    and detects unexpected state mutations that could lead to divergence.
    """
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        super().__init__(config, event_bus)
        
        # State tracking
        self.snapshots: Dict[int, StateSnapshot] = {}  # block_height -> snapshot
        self.max_snapshots = 1000  # Maximum snapshots to keep in memory
        self.expected_app_hashes: Dict[int, str] = {}  # For cross-node comparison
        
        # Divergence detection
        self.divergence_threshold = 3  # Number of consecutive mismatches before alert
        self.consecutive_mismatches = 0
        self.last_known_good_height: Optional[int] = None
        
        # State change tracking
        self.tracked_state_keys: Set[str] = set()  # Keys to specifically monitor
        self.state_change_history: List[Dict[str, Any]] = []
        self.max_change_history = 10000
        
        # Performance tracking
        self.snapshot_times: List[float] = []
        self.max_snapshot_time_ms = 100  # Alert if snapshot takes longer
    
    def initialize(self) -> bool:
        """Initialize the state tracker"""
        logger.info("Initializing State Tracker")
        
        # Load configuration-specific settings
        if 'state_tracker' in self.config.custom_settings:
            settings = self.config.custom_settings['state_tracker']
            self.max_snapshots = settings.get('max_snapshots', self.max_snapshots)
            self.divergence_threshold = settings.get('divergence_threshold', self.divergence_threshold)
            self.tracked_state_keys = set(settings.get('tracked_keys', []))
        
        return True
    
    def register_event_handlers(self):
        """Register event handlers for state-related events"""
        self.event_bus.subscribe(EventType.BLOCK_START, self._on_block_start)
        self.event_bus.subscribe(EventType.BLOCK_END, self._on_block_end)
        self.event_bus.subscribe(EventType.BLOCK_COMMIT, self._on_block_commit)
        self.event_bus.subscribe(EventType.TRANSACTION_END, self._on_transaction_end)
    
    def unregister_event_handlers(self):
        """Unregister event handlers"""
        self.event_bus.unsubscribe(EventType.BLOCK_START, self._on_block_start)
        self.event_bus.unsubscribe(EventType.BLOCK_END, self._on_block_end)
        self.event_bus.unsubscribe(EventType.BLOCK_COMMIT, self._on_block_commit)
        self.event_bus.unsubscribe(EventType.TRANSACTION_END, self._on_transaction_end)
    
    def _on_block_start(self, event: DebugEvent):
        """Handle block start events"""
        if not event.block_height:
            return
        
        # Create initial snapshot for the block
        self._create_snapshot(event.block_height, "pending", event.data)
    
    def _on_block_end(self, event: DebugEvent):
        """Handle block end events"""
        if not event.block_height:
            return
        
        app_hash = event.data.get('app_hash', '')
        
        # Update snapshot with final app hash
        self._update_snapshot(event.block_height, app_hash, event.data)
        
        # Check for divergence
        self._check_for_divergence(event.block_height, app_hash)
    
    def _on_block_commit(self, event: DebugEvent):
        """Handle block commit events"""
        if not event.block_height:
            return
        
        app_hash = event.data.get('app_hash', '')
        
        # Final validation of committed state
        self._validate_committed_state(event.block_height, app_hash)
        
        # Cleanup old snapshots
        self._cleanup_old_snapshots()
    
    def _on_transaction_end(self, event: DebugEvent):
        """Handle transaction end events to track state changes"""
        if not event.block_height or not event.transaction_hash:
            return
        
        # Record state change
        change_record = {
            'transaction_hash': event.transaction_hash,
            'block_height': event.block_height,
            'timestamp': event.timestamp.isoformat(),
            'changes': event.data.get('state_changes', [])
        }
        
        self.state_change_history.append(change_record)
        
        # Trim history if too large
        if len(self.state_change_history) > self.max_change_history:
            self.state_change_history.pop(0)
        
        # Check for suspicious state changes
        self._analyze_state_changes(change_record)
    
    def _create_snapshot(self, block_height: int, app_hash: str, 
                        state_data: Optional[Dict[str, Any]] = None):
        """Create a new state snapshot"""
        start_time = time.time()
        
        try:
            snapshot = StateSnapshot(block_height, app_hash, state_data)
            self.snapshots[block_height] = snapshot
            
            # Emit snapshot event
            snapshot_event = DebugEvent(
                event_type=EventType.STATE_SNAPSHOT,
                severity=Severity.INFO,
                message=f"State snapshot created for block {block_height}",
                block_height=block_height,
                data=snapshot.to_dict()
            )
            self.emit_event(snapshot_event)
            
        except Exception as e:
            logger.error(f"Failed to create state snapshot for block {block_height}: {e}")
        
        finally:
            # Track snapshot creation time
            snapshot_time_ms = (time.time() - start_time) * 1000
            self.snapshot_times.append(snapshot_time_ms)
            
            if snapshot_time_ms > self.max_snapshot_time_ms:
                perf_event = DebugEvent(
                    event_type=EventType.PERFORMANCE_WARNING,
                    severity=Severity.MEDIUM,
                    message=f"Slow state snapshot creation: {snapshot_time_ms:.1f}ms",
                    block_height=block_height,
                    data={'snapshot_time_ms': snapshot_time_ms}
                )
                self.emit_event(perf_event)
    
    def _update_snapshot(self, block_height: int, app_hash: str, 
                        state_data: Optional[Dict[str, Any]] = None):
        """Update an existing snapshot with final data"""
        if block_height in self.snapshots:
            snapshot = self.snapshots[block_height]
            snapshot.app_hash = app_hash
            if state_data:
                snapshot.state_data.update(state_data)
        else:
            # Create new snapshot if it doesn't exist
            self._create_snapshot(block_height, app_hash, state_data)
    
    def _check_for_divergence(self, block_height: int, app_hash: str):
        """Check for potential state divergence"""
        # Check against expected hash if available
        if block_height in self.expected_app_hashes:
            expected_hash = self.expected_app_hashes[block_height]
            if app_hash != expected_hash:
                self.consecutive_mismatches += 1
                
                # Emit divergence event
                divergence_event = create_state_divergence_event(
                    f"App hash mismatch at block {block_height}",
                    block_height,
                    expected_hash,
                    app_hash
                )
                self.emit_event(divergence_event)
                
                # Check if we've exceeded threshold
                if self.consecutive_mismatches >= self.divergence_threshold:
                    critical_event = DebugEvent(
                        event_type=EventType.CRITICAL_ALERT,
                        severity=Severity.CRITICAL,
                        message=f"Critical state divergence: {self.consecutive_mismatches} consecutive mismatches",
                        block_height=block_height,
                        data={
                            'consecutive_mismatches': self.consecutive_mismatches,
                            'threshold': self.divergence_threshold,
                            'last_known_good_height': self.last_known_good_height
                        }
                    )
                    self.emit_event(critical_event)
            else:
                # Reset mismatch counter on successful match
                self.consecutive_mismatches = 0
                self.last_known_good_height = block_height
        
        # Compare with previous block
        self._compare_with_previous_block(block_height)
    
    def _compare_with_previous_block(self, block_height: int):
        """Compare current block with previous block"""
        if block_height <= 1:
            return
        
        previous_height = block_height - 1
        if previous_height not in self.snapshots:
            return
        
        current_snapshot = self.snapshots.get(block_height)
        previous_snapshot = self.snapshots[previous_height]
        
        if not current_snapshot:
            return
        
        # Perform comparison
        comparison = previous_snapshot.compare_with(current_snapshot)
        
        # Emit comparison event
        comparison_event = DebugEvent(
            event_type=EventType.STATE_COMPARISON,
            severity=Severity.INFO,
            message=f"State comparison between blocks {previous_height} and {block_height}",
            block_height=block_height,
            data={
                'comparison': comparison,
                'previous_block': previous_height,
                'current_block': block_height
            }
        )
        self.emit_event(comparison_event)
        
        # Check for suspicious changes
        self._analyze_state_comparison(comparison, block_height)
    
    def _analyze_state_changes(self, change_record: Dict[str, Any]):
        """Analyze state changes for suspicious patterns"""
        changes = change_record.get('changes', [])
        
        # Check for changes to tracked keys
        for change in changes:
            key = change.get('key', '')
            if key in self.tracked_state_keys:
                tracked_change_event = DebugEvent(
                    event_type=EventType.STATE_DIVERGENCE,
                    severity=Severity.MEDIUM,
                    message=f"Change detected in tracked state key: {key}",
                    block_height=change_record['block_height'],
                    transaction_hash=change_record['transaction_hash'],
                    data={
                        'key': key,
                        'old_value': change.get('old_value'),
                        'new_value': change.get('new_value'),
                        'change_type': change.get('type', 'unknown')
                    }
                )
                self.emit_event(tracked_change_event)
        
        # Check for excessive state changes
        if len(changes) > 1000:  # Configurable threshold
            excessive_changes_event = DebugEvent(
                event_type=EventType.PERFORMANCE_WARNING,
                severity=Severity.MEDIUM,
                message=f"Excessive state changes in transaction: {len(changes)}",
                block_height=change_record['block_height'],
                transaction_hash=change_record['transaction_hash'],
                data={'change_count': len(changes)}
            )
            self.emit_event(excessive_changes_event)
    
    def _analyze_state_comparison(self, comparison: Dict[str, Any], block_height: int):
        """Analyze state comparison results for issues"""
        # Check for unexpected key additions/removals
        added_keys = comparison.get('added_keys', [])
        removed_keys = comparison.get('removed_keys', [])
        
        if len(added_keys) > 100:  # Configurable threshold
            mass_addition_event = DebugEvent(
                event_type=EventType.STATE_DIVERGENCE,
                severity=Severity.MEDIUM,
                message=f"Mass state key addition detected: {len(added_keys)} keys",
                block_height=block_height,
                data={'added_keys_count': len(added_keys), 'sample_keys': added_keys[:10]}
            )
            self.emit_event(mass_addition_event)
        
        if len(removed_keys) > 100:  # Configurable threshold
            mass_removal_event = DebugEvent(
                event_type=EventType.STATE_DIVERGENCE,
                severity=Severity.HIGH,
                message=f"Mass state key removal detected: {len(removed_keys)} keys",
                block_height=block_height,
                data={'removed_keys_count': len(removed_keys), 'sample_keys': removed_keys[:10]}
            )
            self.emit_event(mass_removal_event)
    
    def _validate_committed_state(self, block_height: int, app_hash: str):
        """Validate the committed state"""
        # This could include additional validation logic
        # For now, just ensure we have a valid snapshot
        if block_height not in self.snapshots:
            missing_snapshot_event = DebugEvent(
                event_type=EventType.STATE_DIVERGENCE,
                severity=Severity.HIGH,
                message=f"Missing state snapshot for committed block {block_height}",
                block_height=block_height,
                data={'app_hash': app_hash}
            )
            self.emit_event(missing_snapshot_event)
    
    def _cleanup_old_snapshots(self):
        """Remove old snapshots to prevent memory bloat"""
        if len(self.snapshots) <= self.max_snapshots:
            return
        
        # Keep the most recent snapshots
        sorted_heights = sorted(self.snapshots.keys())
        heights_to_remove = sorted_heights[:-self.max_snapshots]
        
        for height in heights_to_remove:
            del self.snapshots[height]
        
        logger.debug(f"Cleaned up {len(heights_to_remove)} old state snapshots")
    
    # Public API methods
    def get_snapshot(self, block_height: int) -> Optional[StateSnapshot]:
        """Get a state snapshot for a specific block height"""
        return self.snapshots.get(block_height)
    
    def get_recent_snapshots(self, count: int = 10) -> List[StateSnapshot]:
        """Get the most recent state snapshots"""
        sorted_heights = sorted(self.snapshots.keys(), reverse=True)
        recent_heights = sorted_heights[:count]
        return [self.snapshots[height] for height in recent_heights]
    
    def set_expected_app_hash(self, block_height: int, app_hash: str):
        """Set expected app hash for divergence detection"""
        self.expected_app_hashes[block_height] = app_hash
    
    def add_tracked_key(self, key: str):
        """Add a state key to track for changes"""
        self.tracked_state_keys.add(key)
    
    def remove_tracked_key(self, key: str):
        """Remove a state key from tracking"""
        self.tracked_state_keys.discard(key)
    
    def get_divergence_summary(self) -> Dict[str, Any]:
        """Get summary of divergence detection status"""
        return {
            'consecutive_mismatches': self.consecutive_mismatches,
            'divergence_threshold': self.divergence_threshold,
            'last_known_good_height': self.last_known_good_height,
            'total_snapshots': len(self.snapshots),
            'tracked_keys_count': len(self.tracked_state_keys),
            'state_changes_tracked': len(self.state_change_history),
            'average_snapshot_time_ms': (
                sum(self.snapshot_times[-100:]) / len(self.snapshot_times[-100:])
                if self.snapshot_times else 0
            )
        }