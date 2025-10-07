"""
Base Analyzer Class

Defines the interface for analyzer plugins that perform detailed analysis
of debugging data and events.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from ..core.config import DebuggerConfig
from ..core.events import EventBus, DebugEvent


class BaseAnalyzer(ABC):
    """Base class for all analyzer plugins"""
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.name = self.__class__.__name__
        self.is_enabled = True
        
        # Analysis results cache
        self.analysis_cache: Dict[str, Any] = {}
        self.max_cache_size = 1000
        
        # Statistics
        self.stats = {
            'analyses_performed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors_encountered': 0
        }
    
    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform analysis on the provided data.
        
        Args:
            data: Data to analyze
            
        Returns:
            Dict containing analysis results
        """
        pass
    
    def can_analyze(self, data: Dict[str, Any]) -> bool:
        """
        Check if this analyzer can process the given data.
        
        Args:
            data: Data to check
            
        Returns:
            bool: True if analyzer can process this data
        """
        return self.is_enabled
    
    def get_cache_key(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Generate a cache key for the given data.
        
        Override this method to enable caching for expensive analyses.
        
        Args:
            data: Data to generate key for
            
        Returns:
            Optional cache key string
        """
        return None
    
    def analyze_with_cache(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform analysis with caching support.
        
        Args:
            data: Data to analyze
            
        Returns:
            Dict containing analysis results
        """
        if not self.can_analyze(data):
            return {'error': 'Analyzer cannot process this data'}
        
        # Check cache if caching is enabled
        cache_key = self.get_cache_key(data)
        if cache_key and cache_key in self.analysis_cache:
            self.stats['cache_hits'] += 1
            return self.analysis_cache[cache_key]
        
        self.stats['cache_misses'] += 1
        
        try:
            # Perform analysis
            result = self.analyze(data)
            self.stats['analyses_performed'] += 1
            
            # Cache result if caching is enabled
            if cache_key:
                self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            self.stats['errors_encountered'] += 1
            return {
                'error': f'Analysis failed: {str(e)}',
                'analyzer': self.name,
                'timestamp': datetime.now().isoformat()
            }
    
    def _cache_result(self, key: str, result: Dict[str, Any]):
        """Cache an analysis result"""
        # Implement LRU-style cache eviction
        if len(self.analysis_cache) >= self.max_cache_size:
            # Remove oldest entry (simple FIFO for now)
            oldest_key = next(iter(self.analysis_cache))
            del self.analysis_cache[oldest_key]
        
        self.analysis_cache[key] = result
    
    def clear_cache(self):
        """Clear the analysis cache"""
        self.analysis_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        stats = self.stats.copy()
        stats['name'] = self.name
        stats['is_enabled'] = self.is_enabled
        stats['cache_size'] = len(self.analysis_cache)
        stats['cache_hit_rate'] = (
            self.stats['cache_hits'] / 
            max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
        )
        return stats
    
    def enable(self):
        """Enable the analyzer"""
        self.is_enabled = True
    
    def disable(self):
        """Disable the analyzer"""
        self.is_enabled = False


class EventAnalyzer(BaseAnalyzer):
    """
    Base class for analyzers that analyze debug events.
    """
    
    def analyze_event(self, event: DebugEvent) -> Dict[str, Any]:
        """
        Analyze a single debug event.
        
        Args:
            event: Debug event to analyze
            
        Returns:
            Dict containing analysis results
        """
        return self.analyze(event.to_dict())
    
    def analyze_events(self, events: List[DebugEvent]) -> Dict[str, Any]:
        """
        Analyze a collection of debug events.
        
        Args:
            events: List of debug events to analyze
            
        Returns:
            Dict containing analysis results
        """
        event_data = [event.to_dict() for event in events]
        return self.analyze({'events': event_data})


class StateAnalyzer(BaseAnalyzer):
    """
    Base class for analyzers that analyze state data.
    """
    
    def analyze_state_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a state snapshot.
        
        Args:
            snapshot: State snapshot data
            
        Returns:
            Dict containing analysis results
        """
        return self.analyze({'type': 'state_snapshot', 'data': snapshot})
    
    def compare_states(self, state1: Dict[str, Any], state2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two state snapshots.
        
        Args:
            state1: First state snapshot
            state2: Second state snapshot
            
        Returns:
            Dict containing comparison results
        """
        return self.analyze({
            'type': 'state_comparison',
            'state1': state1,
            'state2': state2
        })


class TransactionAnalyzer(BaseAnalyzer):
    """
    Base class for analyzers that analyze transaction data.
    """
    
    def analyze_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single transaction.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            Dict containing analysis results
        """
        return self.analyze({'type': 'transaction', 'data': tx_data})
    
    def analyze_transaction_sequence(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a sequence of transactions.
        
        Args:
            transactions: List of transaction data
            
        Returns:
            Dict containing analysis results
        """
        return self.analyze({
            'type': 'transaction_sequence',
            'transactions': transactions
        })