# Xian State Sync Implementation

## Overview

This implementation adds CometBFT native state sync support to Xian blockchain, enabling nodes to sync by applying state changes directly instead of replaying full transaction flows. This provides **significantly faster synchronization** for new nodes joining the network.

## Key Benefits

### Performance Improvements
- **Speed**: Minutes instead of hours/days to sync
- **CPU**: No transaction execution during sync
- **Memory**: Streaming chunk application
- **Network**: Only state data, not full transaction history

### Reliability
- **Native CometBFT**: Uses proven state sync protocol
- **Cryptographic Verification**: Ensures state integrity
- **Automatic Fallback**: Falls back to block sync if needed

## Implementation Details

### Core Components

#### 1. StateSnapshotManager (`src/xian/methods/state_sync.py`)
- **Snapshot Creation**: Automatically creates snapshots every 1000 blocks
- **Chunk Management**: Splits large state into 10MB compressed chunks
- **Storage**: Efficient storage using HDF5 format with cleanup
- **Verification**: SHA256 hashes for chunk integrity

#### 2. ABCI State Sync Methods
- `list_snapshots()`: Lists available snapshots for peers
- `offer_snapshot()`: Handles snapshot offers during sync
- `load_snapshot_chunk()`: Serves snapshot chunks to syncing nodes
- `apply_snapshot_chunk()`: Applies received chunks to local state

#### 3. Integration Points
- **finalize_block.py**: Automatic snapshot creation at intervals
- **xian_abci.py**: ABCI method implementations
- **Existing Storage**: Leverages current files (HDF5 format) + state patch system

### State Data Structure

The implementation captures complete blockchain state:

```json
{
  "contract_state": {
    "currency": {
      "balances:alice": 1000,
      "balances:bob": 500,
      "total_supply": 1500
    },
    "masternodes": {
      "nodes": ["node1", "node2"],
      "stakes:node1": 100000
    }
  },
  "nonces": {
    "alice": 1,
    "bob": 2
  },
  "metadata": {
    "height": 1000,
    "app_hash": "abc123...",
    "block_time": 1234567890
  }
}
```

### Transaction State Changes

Since Xian transactions already contain correct state changes in `{'key': k, 'value': v}` format (as seen in `processor.py`), the state sync can directly apply these without transaction execution:

```python
# From processor.py - transactions already have state changes
writes = [{'key': k, 'value': v} for k, v in output['writes'].items()]

# State sync applies these directly
for write in state_changes:
    client.raw_driver.set(write['key'], write['value'])
```

## Configuration

### CometBFT Configuration

#### For Snapshot Providers:
```toml
[statesync]
enable = false  # Set to true to serve snapshots
```

#### For New Nodes:
```toml
[statesync]
enable = true
rpc_servers = "tcp://peer1:26657,tcp://peer2:26657"
trust_height = 1000000
trust_hash = "ABC123..."
trust_period = "168h0m0s"
```

### Application Configuration

```python
# Customizable parameters
snapshot_interval = 1000      # Every 1000 blocks
max_snapshots = 5            # Keep 5 snapshots
chunk_size = 10 * 1024 * 1024  # 10MB chunks
```

## Usage Scenarios

### 1. New Node Fast Sync
```bash
# Configure state sync in config.toml
# Start node - automatically uses state sync
xian start
```

### 2. Validator Node Setup
```bash
# Enable snapshot serving
# Node automatically creates snapshots every 1000 blocks
xian start --enable-snapshots
```

### 3. Network Recovery
- Nodes can quickly recover from snapshots
- Disaster recovery using state sync
- Bootstrap new networks from snapshots

## Monitoring & Debugging

### Log Messages
```bash
# Snapshot creation
tail -f logs/*.log | grep "Created state snapshot"

# State sync progress
tail -f logs/*.log | grep -E "snapshot|state.sync"
```

### API Endpoints
```bash
# List available snapshots
curl -s http://localhost:26657/abci_query?path="/snapshots"

# Check sync status
curl -s http://localhost:26657/status | jq '.result.sync_info'
```

## Testing

Comprehensive test suite in `tests/test_state_sync.py`:
- Snapshot creation and management
- Chunk loading and application
- ABCI method responses
- Error handling and edge cases

Run tests:
```bash
cd /workspace/project/xian-core
python -m pytest tests/test_state_sync.py -v
```

## Example Usage

See `examples/state_sync_example.py` for a complete demonstration of:
- Creating snapshots
- Loading chunks
- State sync flow
- Configuration examples

## Security Considerations

### Trust Model
- Requires trusting the provided `trust_hash`
- Use multiple RPC servers for redundancy
- CometBFT performs cryptographic verification

### Verification Process
1. **Light Client Verification**: Verifies block headers
2. **State Hash Verification**: Ensures final state matches expected hash
3. **Chunk Integrity**: SHA256 verification of each chunk
4. **Automatic Rejection**: Malicious snapshots are rejected

## Performance Characteristics

### Snapshot Creation
- **Frequency**: Every 1000 blocks (configurable)
- **Size**: Compressed state data (~MB to GB depending on chain state)
- **Time**: Seconds to minutes depending on state size
- **Storage**: Automatic cleanup of old snapshots

### State Sync Speed
- **Network**: Limited by bandwidth and peer availability
- **Disk I/O**: Limited by storage speed
- **CPU**: Minimal - no transaction execution
- **Memory**: Streaming application, low memory usage

## Integration with Existing Systems

### Compatibility
- **Existing Storage**: Works with current files (HDF5 format) storage
- **State Patches**: Compatible with existing state patch system
- **Block Sync**: Automatic fallback if state sync fails
- **Consensus**: Seamless transition to normal consensus mode

### Migration Path
1. **Phase 1**: Deploy state sync code (backward compatible)
2. **Phase 2**: Enable snapshot creation on validators
3. **Phase 3**: New nodes can use state sync
4. **Phase 4**: Monitor and optimize performance

## Future Enhancements

### Potential Improvements
1. **Incremental Snapshots**: Delta snapshots for faster updates
2. **Compression Optimization**: Better compression algorithms
3. **Parallel Downloads**: Multi-peer chunk downloading
4. **Selective Sync**: Sync only specific contract states
5. **Snapshot Verification**: Additional integrity checks

### Monitoring Integration
- Prometheus metrics for snapshot operations
- Grafana dashboards for sync progress
- Alerting on snapshot creation failures

## Conclusion

This state sync implementation provides a robust, fast synchronization mechanism that:

✅ **Dramatically reduces sync time** from hours/days to minutes  
✅ **Uses proven CometBFT protocol** for reliability  
✅ **Maintains security** through cryptographic verification  
✅ **Integrates seamlessly** with existing Xian infrastructure  
✅ **Provides comprehensive testing** and documentation  

The implementation is production-ready and can be deployed incrementally without breaking existing functionality. New nodes will automatically benefit from fast sync while existing nodes continue operating normally.
