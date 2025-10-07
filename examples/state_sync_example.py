#!/usr/bin/env python3
"""
Example demonstrating Xian State Sync functionality

This example shows how to:
1. Enable state sync on a new node
2. Configure snapshot providers
3. Monitor sync progress
"""

import asyncio
import json
from pathlib import Path

from xian.methods.state_sync import StateSnapshotManager
from xian.utils.block import get_latest_block_height, get_latest_block_hash


class MockClient:
    """Mock client for demonstration"""
    def __init__(self):
        self.raw_driver = MockDriver()


class MockDriver:
    """Mock driver for demonstration"""
    def get_contract_files(self):
        return ['currency.d', 'masternodes.d', 'foundation.d']
    
    def items(self, contract_name):
        # Mock contract data
        mock_data = {
            'currency': {
                'balances:alice': 1000.0,
                'balances:bob': 500.0,
                'balances:charlie': 250.0,
                'total_supply': 1750.0
            },
            'masternodes': {
                'nodes': ['node1', 'node2', 'node3'],
                'stakes:node1': 100000,
                'stakes:node2': 150000,
                'stakes:node3': 120000
            },
            'foundation': {
                'owner': 'foundation_address',
                'balance': 50000
            }
        }
        return mock_data.get(contract_name, {})
    
    def set(self, key, value):
        print(f"Setting {key} = {value}")
    
    def hard_apply(self, timestamp):
        print(f"Applying changes at timestamp {timestamp}")


class MockNonceStorage:
    """Mock nonce storage for demonstration"""
    def set_nonce(self, key, value):
        print(f"Setting nonce {key} = {value}")


async def demonstrate_snapshot_creation():
    """Demonstrate creating a state snapshot"""
    print("=== State Snapshot Creation Demo ===")
    
    # Setup
    storage_home = Path("/tmp/xian_demo")
    client = MockClient()
    nonce_storage = MockNonceStorage()
    
    # Create snapshot manager
    snapshot_manager = StateSnapshotManager(storage_home, client, nonce_storage)
    
    # Simulate creating a snapshot at block 1000
    height = 1000
    app_hash = b"demo_app_hash_1234567890abcdef"
    block_time = 1234567890
    
    print(f"Creating snapshot at height {height}")
    snapshot_id = snapshot_manager.create_snapshot(height, app_hash, block_time)
    
    if snapshot_id:
        print(f"✅ Successfully created snapshot: {snapshot_id}")
        
        # List available snapshots
        snapshots = snapshot_manager.list_available_snapshots()
        print(f"📋 Available snapshots: {len(snapshots)}")
        
        for snapshot in snapshots:
            print(f"  - Height: {snapshot.height}, Format: {snapshot.format}, Chunks: {snapshot.chunks}")
    else:
        print("❌ Failed to create snapshot")


async def demonstrate_snapshot_loading():
    """Demonstrate loading snapshot chunks"""
    print("\n=== Snapshot Loading Demo ===")
    
    storage_home = Path("/tmp/xian_demo")
    client = MockClient()
    nonce_storage = MockNonceStorage()
    
    snapshot_manager = StateSnapshotManager(storage_home, client, nonce_storage)
    
    # Try to load chunks from existing snapshot
    snapshots = snapshot_manager.list_available_snapshots()
    
    if snapshots:
        snapshot = snapshots[0]  # Use first available snapshot
        print(f"Loading chunks from snapshot at height {snapshot.height}")
        
        for chunk_index in range(snapshot.chunks):
            chunk_data = snapshot_manager.load_snapshot_chunk(
                snapshot.height, 
                snapshot.format, 
                chunk_index
            )
            
            if chunk_data:
                print(f"✅ Loaded chunk {chunk_index}: {len(chunk_data)} bytes")
            else:
                print(f"❌ Failed to load chunk {chunk_index}")
    else:
        print("No snapshots available for loading")


async def demonstrate_state_sync_flow():
    """Demonstrate complete state sync flow"""
    print("\n=== Complete State Sync Flow Demo ===")
    
    # Simulate a new node syncing from snapshots
    storage_home = Path("/tmp/xian_demo_sync")
    client = MockClient()
    nonce_storage = MockNonceStorage()
    
    sync_manager = StateSnapshotManager(storage_home, client, nonce_storage)
    
    print("🔄 Simulating state sync process...")
    
    # Step 1: Discover available snapshots (from peers)
    print("1. Discovering snapshots from peers...")
    # In real implementation, this would query peers
    
    # Step 2: Select best snapshot
    print("2. Selecting optimal snapshot...")
    
    # Step 3: Download and apply chunks
    print("3. Downloading and applying snapshot chunks...")
    
    # Simulate applying chunks
    test_chunks = [
        b'{"contract_state": {"currency": {"balances:alice": 1000}}}',
        b'{"nonces": {"alice": 1}, "metadata": {"height": 1000}}'
    ]
    
    for i, chunk_data in enumerate(test_chunks):
        success = sync_manager.apply_snapshot_chunk(i, chunk_data)
        if success:
            print(f"  ✅ Applied chunk {i}")
        else:
            print(f"  ❌ Failed to apply chunk {i}")
    
    # Step 4: Finalize restoration
    print("4. Finalizing state restoration...")
    success = sync_manager.finalize_snapshot_restore(len(test_chunks))
    
    if success:
        print("🎉 State sync completed successfully!")
        print("Node is now ready to participate in consensus")
    else:
        print("❌ State sync failed")


def show_configuration_example():
    """Show example CometBFT configuration for state sync"""
    print("\n=== CometBFT Configuration Example ===")
    
    config_example = """
# For Snapshot Providers (add to config.toml):
[statesync]
# Enable serving snapshots to other nodes
enable = false  # Set to true on provider nodes

# For New Nodes (add to config.toml):
[statesync]
enable = true
rpc_servers = "tcp://peer1.xian.network:26657,tcp://peer2.xian.network:26657"
trust_height = 1000000
trust_hash = "ABC123DEF456..."  # Get from: curl -s https://rpc.xian.network:26657/commit
trust_period = "168h0m0s"  # 1 week
discovery_time = "15s"
temp_dir = ""

# Application-specific settings (in your node startup):
snapshot_interval = 1000      # Create snapshot every 1000 blocks
max_snapshots = 5            # Keep 5 most recent snapshots
chunk_size = 10485760        # 10MB chunks
"""
    
    print(config_example)


async def main():
    """Run all demonstrations"""
    print("🚀 Xian State Sync Demonstration")
    print("=" * 50)
    
    try:
        await demonstrate_snapshot_creation()
        await demonstrate_snapshot_loading()
        await demonstrate_state_sync_flow()
        show_configuration_example()
        
        print("\n✨ Demo completed successfully!")
        print("\nNext steps:")
        print("1. Configure your CometBFT node with state sync settings")
        print("2. Start your node - it will automatically use state sync if enabled")
        print("3. Monitor logs for sync progress")
        print("4. Once synced, your node will switch to normal consensus mode")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())