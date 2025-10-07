# Xian State Sync Guide

This guide explains how to use CometBFT's native state sync feature with Xian blockchain for fast synchronization.

## Overview

State sync allows new nodes to join the network quickly by downloading application state snapshots instead of replaying all transactions from genesis. This is significantly faster than traditional block sync.

## How It Works

1. **Snapshot Creation**: Validator nodes automatically create state snapshots every 1000 blocks
2. **Snapshot Distribution**: New nodes can request these snapshots from peers
3. **Fast Sync**: New nodes apply state changes directly without transaction execution
4. **Verification**: CometBFT verifies the final state using cryptographic proofs

## Configuration

### For Snapshot Providers (Validators)

Add to your `config.toml`:

```toml
#######################################################
###       State Sync Configuration Options          ###
#######################################################
[statesync]
# State sync rapidly bootstraps a new node by discovering, fetching, and restoring a state machine
# snapshot from peers instead of fetching and replaying historical blocks. Requires some peers in
# the network to take and serve state machine snapshots. State sync is not attempted if the node
# has any local state (LastBlockHeight > 0). The node will have a truncated block history,
# starting from the height of the snapshot.
enable = false

# RPC servers (comma-separated) for light client verification of the synced state machine and
# retrieval of state data for node bootstrapping. Also needs a trusted height and corresponding
# header hash obtained from a trusted source, and a period during which validators can be trusted.
#
# For Cosmos SDK-based chains, trust_period should usually be about 2/3 of the unbonding period
# (~2 weeks) during which they can be financially punished (slashed) for misbehavior.
rpc_servers = ""
trust_height = 0
trust_hash = ""
trust_period = "168h0m0s"

# Time to spend discovering snapshots before initiating a restore.
discovery_time = "15s"

# Temporary directory for state sync snapshot chunks.
temp_dir = ""
```

### For New Nodes (State Sync Clients)

1. **Enable State Sync** in `config.toml`:

```toml
[statesync]
enable = true
rpc_servers = "tcp://peer1:26657,tcp://peer2:26657"
trust_height = 1000000  # Recent block height
trust_hash = "ABC123..."  # Block hash at trust_height
trust_period = "168h0m0s"  # ~1 week
```

2. **Get Trust Height and Hash**:

```bash
# Query a trusted RPC endpoint
curl -s https://rpc.xian.network:26657/commit | jq '{height: .result.signed_header.header.height, hash: .result.signed_header.commit.block_id.hash}'
```

3. **Start the Node**:

```bash
xian start
```

## Snapshot Configuration

The Xian application creates snapshots with these default settings:

- **Snapshot Interval**: Every 1000 blocks
- **Chunk Size**: 10MB per chunk
- **Max Snapshots**: Keep 5 most recent snapshots
- **Compression**: Gzip compression for efficient storage

These can be customized by modifying the `StateSnapshotManager` configuration.

## State Sync Process

### 1. Snapshot Discovery
- Node queries peers for available snapshots
- Selects the most recent compatible snapshot

### 2. Snapshot Download
- Downloads snapshot in chunks from multiple peers
- Verifies chunk integrity using cryptographic hashes

### 3. State Application
- Applies state changes directly to storage
- Bypasses transaction execution for speed
- Maintains all contract state, balances, and nonces

### 4. Verification
- CometBFT verifies final app_hash matches expected value
- Node switches to normal consensus mode

## Benefits

### Speed Comparison
- **Traditional Sync**: Hours to days depending on chain history
- **State Sync**: Minutes to sync to latest state

### Resource Usage
- **Lower CPU**: No transaction execution during sync
- **Lower Memory**: Streaming chunk application
- **Lower Network**: Only state data, not full transaction history

## Monitoring

### Logs to Watch

```bash
# Snapshot creation (on providers)
tail -f logs/*.log | grep "Created state snapshot"

# State sync progress (on new nodes)
tail -f logs/*.log | grep -E "snapshot|state.sync"
```

### Metrics

- Snapshot creation time
- Chunk download speed
- State application progress
- Final verification status

## Troubleshooting

### Common Issues

1. **No Snapshots Available**
   - Ensure provider nodes have snapshots enabled
   - Check network connectivity to RPC servers

2. **Trust Hash Mismatch**
   - Verify trust_height and trust_hash are correct
   - Use recent values (within trust_period)

3. **Chunk Download Failures**
   - Check peer connectivity
   - Verify firewall settings allow P2P connections

4. **State Application Errors**
   - Check disk space availability
   - Verify storage permissions

### Debug Commands

```bash
# Check available snapshots
curl -s http://localhost:26657/abci_query?path="/snapshots"

# Monitor sync status
curl -s http://localhost:26657/status | jq '.result.sync_info'

# Check peer connections
curl -s http://localhost:26657/net_info | jq '.result.peers'
```

## Security Considerations

### Trust Model
- State sync requires trusting the provided trust_hash
- Use multiple RPC servers for redundancy
- Verify trust_hash through multiple sources

### Verification
- CometBFT performs cryptographic verification of final state
- Light client verification ensures state integrity
- Malicious snapshots will be rejected automatically

## Advanced Configuration

### Custom Snapshot Intervals

Modify `StateSnapshotManager` initialization:

```python
self.snapshot_manager = StateSnapshotManager(
    storage_home,
    client,
    nonce_storage,
    snapshot_interval=500,  # Every 500 blocks
    max_snapshots=10,       # Keep 10 snapshots
    chunk_size=5*1024*1024  # 5MB chunks
)
```

### Selective State Sync

For development or testing, you can create snapshots with specific state:

```python
# Create snapshot with only essential state
snapshot_manager.create_selective_snapshot(
    height=height,
    app_hash=app_hash,
    include_contracts=['currency', 'masternodes'],
    exclude_patterns=['*.test.*']
)
```

## Performance Tuning

### Network Optimization
- Use multiple RPC servers for parallel downloads
- Configure appropriate chunk sizes for network conditions
- Enable compression for slower connections

### Storage Optimization
- Use fast SSD storage for snapshot creation/application
- Configure appropriate temp_dir location
- Monitor disk space usage

### Memory Optimization
- Adjust chunk sizes based on available RAM
- Use streaming application for large states
- Configure garbage collection appropriately

## Integration with Existing Tools

### Monitoring
- Prometheus metrics for snapshot operations
- Grafana dashboards for sync progress
- Alert on snapshot creation failures

### Backup/Recovery
- Snapshots can serve as state backups
- Automated snapshot archival to cloud storage
- Disaster recovery using state sync

This implementation provides a robust, fast synchronization mechanism that significantly improves the node onboarding experience for the Xian blockchain.