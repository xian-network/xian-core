"""
Cache Monitor

Monitors cache usage and detects cache leaks, pollution, and cleanup failures
that could lead to state divergence between nodes.
"""

import gc
import sys
import weakref
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger

try:
    from typing import WeakSet
except ImportError:
    # For Python < 3.9, WeakSet is not in typing
    from weakref import WeakSet

from .base import BaseMonitor
from ..core.config import DebuggerConfig
from ..core.events import (
    EventBus, DebugEvent, EventType, Severity,
    create_cache_leak_event
)


class CacheEntry:
    """Represents a cache entry with metadata"""
    
    def __init__(self, key: str, value: Any, source: str):
        self.key = key
        self.value = value
        self.source = source  # Where this cache entry originated
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.access_count = 1
        self.size_bytes = self._estimate_size(value)
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate memory size of an object"""
        try:
            return sys.getsizeof(obj)
        except:
            return 0
    
    def access(self):
        """Record an access to this cache entry"""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def idle_seconds(self) -> float:
        """Get idle time since last access in seconds"""
        return (datetime.now() - self.last_accessed).total_seconds()


class CacheMonitor(BaseMonitor):
    """
    Monitors cache usage and detects potential issues.
    
    This monitor tracks cache entries across different components,
    detects leaks, monitors cleanup, and identifies pollution patterns.
    """
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        super().__init__(config, event_bus)
        
        # Cache tracking
        self.monitored_caches: Dict[str, WeakSet] = defaultdict(WeakSet)
        self.cache_snapshots: List[Dict[str, Any]] = []
        self.max_snapshots = 100
        
        # Leak detection
        self.baseline_cache_sizes: Dict[str, int] = {}
        self.leak_threshold_multiplier = 2.0  # Alert if cache grows 2x baseline
        self.leak_detection_interval = 60  # seconds
        self.last_leak_check = datetime.now()
        
        # Cache entry tracking
        self.tracked_entries: Dict[str, CacheEntry] = {}
        self.max_tracked_entries = 10000
        
        # Pollution detection
        self.expected_cache_patterns: Dict[str, Set[str]] = {}
        self.pollution_threshold = 0.3  # 30% unexpected entries
        
        # Performance tracking
        self.cache_access_times: Dict[str, List[float]] = defaultdict(list)
        self.slow_access_threshold_ms = 10.0
        
        # Statistics
        self.leak_events_emitted = 0
        self.pollution_events_emitted = 0
        self.cleanup_failures_detected = 0
    
    def initialize(self) -> bool:
        """Initialize the cache monitor"""
        logger.info("Initializing Cache Monitor")
        
        # Load configuration
        if 'cache_monitor' in self.config.custom_settings:
            settings = self.config.custom_settings['cache_monitor']
            self.leak_threshold_multiplier = settings.get('leak_threshold_multiplier', self.leak_threshold_multiplier)
            self.leak_detection_interval = settings.get('leak_detection_interval', self.leak_detection_interval)
            self.pollution_threshold = settings.get('pollution_threshold', self.pollution_threshold)
        
        # Initialize baseline measurements
        self._establish_baselines()
        
        return True
    
    def should_run_continuously(self) -> bool:
        """Cache monitor runs continuously"""
        return True
    
    def get_check_interval(self) -> float:
        """Check every 30 seconds"""
        return 30.0
    
    def check(self):
        """Perform cache monitoring checks"""
        try:
            # Take cache snapshot
            self._take_cache_snapshot()
            
            # Check for leaks
            if self._should_check_leaks():
                self._check_for_leaks()
            
            # Check for pollution
            self._check_for_pollution()
            
            # Check for cleanup failures
            self._check_cleanup_failures()
            
            # Monitor performance
            self._monitor_cache_performance()
            
            # Cleanup old tracking data
            self._cleanup_tracking_data()
            
        except Exception as e:
            logger.error(f"Error in cache monitoring: {e}")
            self.stats['errors_encountered'] += 1
    
    def _establish_baselines(self):
        """Establish baseline cache sizes"""
        # This would be called after system initialization
        # For now, we'll establish baselines on first check
        pass
    
    def _take_cache_snapshot(self):
        """Take a snapshot of current cache state"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'caches': {},
            'total_entries': 0,
            'total_memory_mb': 0
        }
        
        for cache_name, cache_refs in self.monitored_caches.items():
            # Count live references
            live_refs = [ref for ref in cache_refs if ref() is not None]
            cache_size = len(live_refs)
            
            snapshot['caches'][cache_name] = {
                'size': cache_size,
                'live_refs': cache_size
            }
            snapshot['total_entries'] += cache_size
        
        # Estimate total memory usage
        snapshot['total_memory_mb'] = sum(
            entry.size_bytes for entry in self.tracked_entries.values()
        ) / (1024 * 1024)
        
        self.cache_snapshots.append(snapshot)
        
        # Trim old snapshots
        if len(self.cache_snapshots) > self.max_snapshots:
            self.cache_snapshots.pop(0)
    
    def _should_check_leaks(self) -> bool:
        """Determine if we should check for leaks"""
        return (datetime.now() - self.last_leak_check).total_seconds() >= self.leak_detection_interval
    
    def _check_for_leaks(self):
        """Check for cache leaks"""
        self.last_leak_check = datetime.now()
        
        for cache_name, cache_refs in self.monitored_caches.items():
            current_size = len([ref for ref in cache_refs if ref() is not None])
            baseline_size = self.baseline_cache_sizes.get(cache_name, 0)
            
            # Update baseline if this is first check
            if baseline_size == 0:
                self.baseline_cache_sizes[cache_name] = current_size
                continue
            
            # Check for significant growth
            if current_size > baseline_size * self.leak_threshold_multiplier:
                growth_factor = current_size / max(1, baseline_size)
                
                # Identify leaked entries
                leaked_keys = self._identify_leaked_entries(cache_name)
                
                leak_event = create_cache_leak_event(
                    f"Cache leak detected in {cache_name}: {current_size} entries "
                    f"({growth_factor:.1f}x baseline of {baseline_size})",
                    leaked_keys
                )
                leak_event.data.update({
                    'cache_name': cache_name,
                    'current_size': current_size,
                    'baseline_size': baseline_size,
                    'growth_factor': growth_factor
                })
                
                self.emit_event(leak_event)
                self.leak_events_emitted += 1
                
                # Update baseline to prevent spam
                self.baseline_cache_sizes[cache_name] = current_size
    
    def _identify_leaked_entries(self, cache_name: str) -> List[str]:
        """Identify potentially leaked cache entries"""
        leaked_keys = []
        
        # Look for entries that are old and haven't been accessed recently
        for key, entry in self.tracked_entries.items():
            if (entry.source == cache_name and 
                entry.age_seconds() > 300 and  # Older than 5 minutes
                entry.idle_seconds() > 180):   # Not accessed in 3 minutes
                leaked_keys.append(key)
        
        return leaked_keys[:50]  # Limit to first 50 for reporting
    
    def _check_for_pollution(self):
        """Check for cache pollution"""
        for cache_name, expected_patterns in self.expected_cache_patterns.items():
            if cache_name not in self.monitored_caches:
                continue
            
            # Get current cache keys
            current_keys = set()
            for entry_key, entry in self.tracked_entries.items():
                if entry.source == cache_name:
                    current_keys.add(entry.key)
            
            if not current_keys:
                continue
            
            # Check for unexpected keys
            unexpected_keys = current_keys - expected_patterns
            pollution_ratio = len(unexpected_keys) / len(current_keys)
            
            if pollution_ratio > self.pollution_threshold:
                pollution_event = DebugEvent(
                    event_type=EventType.CACHE_POLLUTION,
                    severity=Severity.MEDIUM,
                    message=f"Cache pollution detected in {cache_name}: "
                           f"{pollution_ratio:.1%} unexpected entries",
                    data={
                        'cache_name': cache_name,
                        'pollution_ratio': pollution_ratio,
                        'unexpected_keys_count': len(unexpected_keys),
                        'sample_unexpected_keys': list(unexpected_keys)[:10],
                        'total_keys': len(current_keys)
                    }
                )
                
                self.emit_event(pollution_event)
                self.pollution_events_emitted += 1
    
    def _check_cleanup_failures(self):
        """Check for cache cleanup failures"""
        # Look for entries that should have been cleaned up
        stale_entries = []
        
        for key, entry in self.tracked_entries.items():
            # Consider entries stale if they're old and haven't been accessed
            if (entry.age_seconds() > 600 and  # Older than 10 minutes
                entry.idle_seconds() > 300):   # Not accessed in 5 minutes
                stale_entries.append(entry)
        
        if len(stale_entries) > 100:  # Threshold for cleanup failure
            cleanup_event = DebugEvent(
                event_type=EventType.CACHE_CLEANUP_FAILURE,
                severity=Severity.MEDIUM,
                message=f"Cache cleanup failure: {len(stale_entries)} stale entries detected",
                data={
                    'stale_entries_count': len(stale_entries),
                    'sample_stale_keys': [entry.key for entry in stale_entries[:10]],
                    'oldest_entry_age_seconds': max(entry.age_seconds() for entry in stale_entries)
                }
            )
            
            self.emit_event(cleanup_event)
            self.cleanup_failures_detected += 1
    
    def _monitor_cache_performance(self):
        """Monitor cache access performance"""
        for cache_name, access_times in self.cache_access_times.items():
            if not access_times:
                continue
            
            # Check recent access times
            recent_times = access_times[-100:]  # Last 100 accesses
            avg_time_ms = sum(recent_times) / len(recent_times)
            
            if avg_time_ms > self.slow_access_threshold_ms:
                perf_event = DebugEvent(
                    event_type=EventType.PERFORMANCE_WARNING,
                    severity=Severity.MEDIUM,
                    message=f"Slow cache access in {cache_name}: {avg_time_ms:.1f}ms average",
                    data={
                        'cache_name': cache_name,
                        'average_access_time_ms': avg_time_ms,
                        'threshold_ms': self.slow_access_threshold_ms,
                        'sample_size': len(recent_times)
                    }
                )
                
                self.emit_event(perf_event)
    
    def _cleanup_tracking_data(self):
        """Clean up old tracking data"""
        # Remove old cache entries
        if len(self.tracked_entries) > self.max_tracked_entries:
            # Sort by last access time and remove oldest
            sorted_entries = sorted(
                self.tracked_entries.items(),
                key=lambda x: x[1].last_accessed
            )
            
            entries_to_remove = len(self.tracked_entries) - self.max_tracked_entries
            for i in range(entries_to_remove):
                key, _ = sorted_entries[i]
                del self.tracked_entries[key]
        
        # Clean up access time history
        for cache_name in self.cache_access_times:
            times = self.cache_access_times[cache_name]
            if len(times) > 1000:
                self.cache_access_times[cache_name] = times[-500:]  # Keep last 500
    
    # Public API for instrumentation
    def register_cache(self, cache_name: str, cache_obj: Any):
        """Register a cache object for monitoring"""
        if cache_obj is not None:
            self.monitored_caches[cache_name].add(weakref.ref(cache_obj))
            logger.debug(f"Registered cache for monitoring: {cache_name}")
    
    def track_cache_entry(self, cache_name: str, key: str, value: Any):
        """Track a specific cache entry"""
        entry_key = f"{cache_name}:{key}"
        
        if entry_key in self.tracked_entries:
            self.tracked_entries[entry_key].access()
        else:
            self.tracked_entries[entry_key] = CacheEntry(key, value, cache_name)
    
    def record_cache_access(self, cache_name: str, access_time_ms: float):
        """Record cache access time"""
        self.cache_access_times[cache_name].append(access_time_ms)
    
    def set_expected_pattern(self, cache_name: str, expected_keys: Set[str]):
        """Set expected cache key patterns for pollution detection"""
        self.expected_cache_patterns[cache_name] = expected_keys
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache monitoring statistics"""
        total_tracked_entries = len(self.tracked_entries)
        total_monitored_caches = len(self.monitored_caches)
        
        # Calculate memory usage
        total_memory_mb = sum(
            entry.size_bytes for entry in self.tracked_entries.values()
        ) / (1024 * 1024)
        
        # Get cache sizes
        cache_sizes = {}
        for cache_name, cache_refs in self.monitored_caches.items():
            live_refs = [ref for ref in cache_refs if ref() is not None]
            cache_sizes[cache_name] = len(live_refs)
        
        return {
            'total_tracked_entries': total_tracked_entries,
            'total_monitored_caches': total_monitored_caches,
            'total_memory_mb': total_memory_mb,
            'cache_sizes': cache_sizes,
            'baseline_sizes': self.baseline_cache_sizes.copy(),
            'leak_events_emitted': self.leak_events_emitted,
            'pollution_events_emitted': self.pollution_events_emitted,
            'cleanup_failures_detected': self.cleanup_failures_detected,
            'snapshots_taken': len(self.cache_snapshots)
        }
    
    def get_recent_snapshots(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent cache snapshots"""
        return self.cache_snapshots[-count:]
    
    def force_leak_check(self):
        """Force an immediate leak check"""
        self._check_for_leaks()
    
    def reset_baselines(self):
        """Reset cache size baselines"""
        self.baseline_cache_sizes.clear()
        logger.info("Cache baselines reset")