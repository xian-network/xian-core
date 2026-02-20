#!/usr/bin/env python3
"""
State Sync Demonstration Script

This script demonstrates the core concepts of the CometBFT State Sync implementation
for Xian blockchain without requiring full dependencies.

Key Features Demonstrated:
1. Snapshot creation logic
2. State data collection simulation
3. Chunk creation and compression
4. Snapshot restoration process
"""

import json
import gzip
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import time


class MockStateSnapshotManager:
    """
    Simplified version of StateSnapshotManager for demonstration
    """
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.snapshots_dir = storage_path / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_interval = 1000
        self.max_chunk_size = 10 * 1024 * 1024  # 10MB
    
    def should_create_snapshot(self, height: int) -> bool:
        """Check if snapshot should be created at this height"""
        return height > 0 and height % self.snapshot_interval == 0
    
    def create_mock_state_data(self, height: int) -> Dict[str, Any]:
        """Create mock state data for demonstration"""
        return {
            'contract_state': {
                'currency': {
                    'balances:alice': 1000 + height,
                    'balances:bob': 500 + height // 2,
                    'balances:charlie': 250 + height // 4
                },
                'masternodes': {
                    'nodes': [f'node_{i}' for i in range(1, 6)],
                    'stakes': {f'node_{i}': 10000 + i * 1000 for i in range(1, 6)}
                },
                'governance': {
                    'proposals': [f'proposal_{i}' for i in range(1, 4)],
                    'votes': {f'proposal_{i}': {'yes': i * 10, 'no': i * 5} for i in range(1, 4)}
                }
            },
            'nonces': {
                'alice': height // 100,
                'bob': height // 200,
                'charlie': height // 300
            },
            'metadata': {
                'height': height,
                'app_hash': hashlib.sha256(f'block_{height}'.encode()).hexdigest(),
                'block_time': str(int(time.time())),
                'chain_id': 'xian-mainnet'
            }
        }
    
    def create_chunks(self, data: Dict[str, Any]) -> List[bytes]:
        """Create compressed chunks from state data"""
        json_data = json.dumps(data, sort_keys=True).encode()
        compressed = gzip.compress(json_data, compresslevel=6)
        
        chunks = []
        for i in range(0, len(compressed), self.max_chunk_size):
            chunk = compressed[i:i + self.max_chunk_size]
            chunks.append(chunk)
        
        return chunks
    
    def create_snapshot(self, height: int) -> str:
        """Create a snapshot at the given height"""
        print(f"📸 Creating snapshot at height {height}...")
        
        # Collect state data
        state_data = self.create_mock_state_data(height)
        print(f"   📊 Collected state data: {len(json.dumps(state_data))} bytes")
        
        # Create chunks
        chunks = self.create_chunks(state_data)
        print(f"   📦 Created {len(chunks)} chunks")
        
        # Generate snapshot ID
        snapshot_id = f"snapshot_{height}_{int(time.time())}"
        snapshot_dir = self.snapshots_dir / snapshot_id
        snapshot_dir.mkdir(exist_ok=True)
        
        # Save chunks
        chunk_hashes = []
        for i, chunk in enumerate(chunks):
            chunk_file = snapshot_dir / f"chunk_{i}.gz"
            with open(chunk_file, 'wb') as f:
                f.write(chunk)
            
            chunk_hash = hashlib.sha256(chunk).hexdigest()
            chunk_hashes.append(chunk_hash)
            print(f"   💾 Saved chunk {i}: {len(chunk)} bytes, hash: {chunk_hash[:16]}...")
        
        # Save metadata
        metadata = {
            'height': height,
            'format': 1,
            'chunks': len(chunks),
            'app_hash': state_data['metadata']['app_hash'],
            'block_time': state_data['metadata']['block_time'],
            'chunk_hashes': chunk_hashes,
            'total_size': sum(len(chunk) for chunk in chunks)
        }
        
        metadata_file = snapshot_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"   ✅ Snapshot {snapshot_id} created successfully")
        print(f"   📈 Total size: {metadata['total_size']} bytes")
        return snapshot_id
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List available snapshots"""
        snapshots = []
        
        for snapshot_dir in self.snapshots_dir.iterdir():
            if snapshot_dir.is_dir():
                metadata_file = snapshot_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    snapshots.append({
                        'id': snapshot_dir.name,
                        'height': metadata['height'],
                        'chunks': metadata['chunks'],
                        'size': metadata['total_size'],
                        'app_hash': metadata['app_hash'][:16] + '...'
                    })
        
        return sorted(snapshots, key=lambda x: x['height'], reverse=True)
    
    def restore_from_snapshot(self, snapshot_id: str) -> bool:
        """Simulate restoring state from a snapshot"""
        print(f"🔄 Restoring from snapshot {snapshot_id}...")
        
        snapshot_dir = self.snapshots_dir / snapshot_id
        if not snapshot_dir.exists():
            print(f"   ❌ Snapshot {snapshot_id} not found")
            return False
        
        # Load metadata
        metadata_file = snapshot_dir / "metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        print(f"   📋 Snapshot metadata: height={metadata['height']}, chunks={metadata['chunks']}")
        
        # Load and reconstruct chunks
        reconstructed_data = b''
        for i in range(metadata['chunks']):
            chunk_file = snapshot_dir / f"chunk_{i}.gz"
            with open(chunk_file, 'rb') as f:
                chunk = f.read()
            
            # Verify chunk hash
            chunk_hash = hashlib.sha256(chunk).hexdigest()
            expected_hash = metadata['chunk_hashes'][i]
            if chunk_hash != expected_hash:
                print(f"   ❌ Chunk {i} hash mismatch")
                return False
            
            reconstructed_data += chunk
            print(f"   ✅ Loaded chunk {i}: {len(chunk)} bytes")
        
        # Decompress and parse
        try:
            decompressed = gzip.decompress(reconstructed_data)
            state_data = json.loads(decompressed.decode())
            
            print(f"   📊 Restored state data: {len(decompressed)} bytes")
            print(f"   🏛️  Contract state keys: {list(state_data['contract_state'].keys())}")
            print(f"   🔢 Nonces: {len(state_data['nonces'])} accounts")
            print(f"   📈 Block height: {state_data['metadata']['height']}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Failed to restore: {e}")
            return False


def main():
    """Main demonstration function"""
    print("🚀 Xian State Sync Demonstration")
    print("=" * 50)
    
    # Create temporary storage
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir)
        manager = MockStateSnapshotManager(storage_path)
        
        print(f"📁 Using storage: {storage_path}")
        print()
        
        # Simulate blockchain progression with snapshots
        heights = [1000, 2000, 3000, 4000, 5000]
        snapshot_ids = []
        
        for height in heights:
            if manager.should_create_snapshot(height):
                snapshot_id = manager.create_snapshot(height)
                snapshot_ids.append(snapshot_id)
                print()
        
        # List available snapshots
        print("📋 Available Snapshots:")
        print("-" * 30)
        snapshots = manager.list_snapshots()
        for snapshot in snapshots:
            print(f"   ID: {snapshot['id']}")
            print(f"   Height: {snapshot['height']}")
            print(f"   Chunks: {snapshot['chunks']}")
            print(f"   Size: {snapshot['size']} bytes")
            print(f"   Hash: {snapshot['app_hash']}")
            print()
        
        # Demonstrate restoration
        if snapshot_ids:
            latest_snapshot = snapshot_ids[-1]
            print(f"🔄 Demonstrating restoration from latest snapshot...")
            print("-" * 50)
            success = manager.restore_from_snapshot(latest_snapshot)
            
            if success:
                print("✅ State sync demonstration completed successfully!")
            else:
                print("❌ State sync demonstration failed!")
        
        print()
        print("💡 Key Benefits of State Sync:")
        print("   • Fast node synchronization (minutes vs hours/days)")
        print("   • Reduced bandwidth usage")
        print("   • Lower storage requirements for new nodes")
        print("   • Automatic fallback to block sync if needed")
        print("   • Cryptographic verification of state integrity")


if __name__ == "__main__":
    main()