"""
Tests for State Sync functionality
"""
import unittest
import tempfile
import json
import gzip
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from xian.methods.state_sync import StateSnapshotManager
from cometbft.abci.v1beta3.types_pb2 import (
    ResponseListSnapshots,
    ResponseOfferSnapshot,
    ResponseLoadSnapshotChunk,
    ResponseApplySnapshotChunk,
    Snapshot
)


class TestStateSnapshotManager:
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_client(self):
        """Mock contracting client"""
        client = Mock()
        client.raw_driver = Mock()
        client.raw_driver.get_contract_files.return_value = ['currency.d', 'masternodes.d']
        client.raw_driver.items.return_value = {
            'currency.balances:alice': 1000,
            'currency.balances:bob': 500,
            'masternodes.nodes': ['node1', 'node2']
        }
        client.raw_driver.set = Mock()
        client.raw_driver.hard_apply = Mock()
        return client
    
    @pytest.fixture
    def mock_nonce_storage(self):
        """Mock nonce storage"""
        nonce_storage = Mock()
        nonce_storage.set_nonce = Mock()
        return nonce_storage
    
    @pytest.fixture
    def snapshot_manager(self, temp_storage, mock_client, mock_nonce_storage):
        """Create StateSnapshotManager instance"""
        return StateSnapshotManager(temp_storage, mock_client, mock_nonce_storage)
    
    def test_should_create_snapshot(self, snapshot_manager):
        """Test snapshot creation interval logic"""
        # Should create at interval blocks
        assert snapshot_manager.should_create_snapshot(1000) == True
        assert snapshot_manager.should_create_snapshot(2000) == True
        assert snapshot_manager.should_create_snapshot(5000) == True
        
        # Should not create at other blocks
        assert snapshot_manager.should_create_snapshot(999) == False
        assert snapshot_manager.should_create_snapshot(1001) == False
        assert snapshot_manager.should_create_snapshot(1500) == False
    
    def test_create_snapshot(self, snapshot_manager, temp_storage):
        """Test snapshot creation"""
        height = 1000
        app_hash = b"test_hash_123456"
        block_time = 1234567890
        
        # Mock get_latest_block_height and get_latest_block_hash
        with pytest.MonkeyPatch().context() as m:
            m.setattr("xian.methods.state_sync.get_latest_block_height", lambda: height)
            m.setattr("xian.methods.state_sync.get_latest_block_hash", lambda: app_hash)
            
            snapshot_id = snapshot_manager.create_snapshot(height, app_hash, block_time)
        
        assert snapshot_id is not None
        assert snapshot_id.startswith(f"{height}_")
        
        # Check snapshot directory was created
        snapshot_dir = temp_storage / "snapshots" / f"snapshot_{snapshot_id}"
        assert snapshot_dir.exists()
        
        # Check metadata file
        metadata_file = snapshot_dir / "metadata.json"
        assert metadata_file.exists()
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata["height"] == height
        assert metadata["app_hash"] == app_hash.hex()
        assert metadata["block_time"] == block_time
        assert metadata["format"] == 1
        assert "chunks" in metadata
        assert "chunk_hashes" in metadata
    
    def test_list_available_snapshots(self, snapshot_manager, temp_storage):
        """Test listing available snapshots"""
        # Create a test snapshot directory with metadata
        snapshot_dir = temp_storage / "snapshots" / "snapshot_1000_abcd1234"
        snapshot_dir.mkdir(parents=True)
        
        metadata = {
            "height": 1000,
            "app_hash": "abcd1234567890",
            "block_time": 1234567890,
            "format": 1,
            "chunks": 2,
            "chunk_hashes": ["hash1", "hash2"],
            "created_at": 1234567890
        }
        
        metadata_file = snapshot_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        # List snapshots
        snapshots = snapshot_manager.list_available_snapshots()
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.height == 1000
        assert snapshot.format == 1
        assert snapshot.chunks == 2
        assert snapshot.hash == bytes.fromhex("abcd1234567890")
    
    def test_load_snapshot_chunk(self, snapshot_manager, temp_storage):
        """Test loading snapshot chunks"""
        # Create test snapshot with chunks
        snapshot_dir = temp_storage / "snapshots" / "snapshot_1000_abcd1234"
        snapshot_dir.mkdir(parents=True)
        
        # Create metadata
        metadata = {
            "height": 1000,
            "app_hash": "abcd1234567890",
            "format": 1,
            "chunks": 2,
            "chunk_hashes": ["hash1", "hash2"]
        }
        
        with open(snapshot_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f)
        
        # Create test chunks
        test_data_1 = b"test chunk data 1"
        test_data_2 = b"test chunk data 2"
        
        with gzip.open(snapshot_dir / "chunk_0000.gz", 'wb') as f:
            f.write(test_data_1)
        
        with gzip.open(snapshot_dir / "chunk_0001.gz", 'wb') as f:
            f.write(test_data_2)
        
        # Load chunks
        chunk_0 = snapshot_manager.load_snapshot_chunk(1000, 1, 0)
        chunk_1 = snapshot_manager.load_snapshot_chunk(1000, 1, 1)
        
        assert chunk_0 == test_data_1
        assert chunk_1 == test_data_2
        
        # Test non-existent chunk
        chunk_missing = snapshot_manager.load_snapshot_chunk(1000, 1, 999)
        assert chunk_missing is None
    
    def test_apply_snapshot_chunk(self, snapshot_manager, temp_storage):
        """Test applying snapshot chunks"""
        test_data = b"test chunk data for application"
        
        # Apply chunk
        success = snapshot_manager.apply_snapshot_chunk(0, test_data)
        assert success == True
        
        # Check chunk was stored
        temp_dir = temp_storage / "snapshots" / "temp_restore"
        chunk_file = temp_dir / "chunk_0000"
        assert chunk_file.exists()
        
        with open(chunk_file, 'rb') as f:
            stored_data = f.read()
        
        assert stored_data == test_data
    
    def test_finalize_snapshot_restore(self, snapshot_manager, temp_storage, mock_client):
        """Test finalizing snapshot restoration"""
        # Create temp chunks
        temp_dir = temp_storage / "snapshots" / "temp_restore"
        temp_dir.mkdir(parents=True)
        
        # Create test state data
        state_data = {
            "contract_state": {
                "currency": {
                    "balances:alice": 1000,
                    "balances:bob": 500
                }
            },
            "nonces": {
                "alice": 1,
                "bob": 2
            },
            "metadata": {
                "height": 1000,
                "app_hash": "abcd1234",
                "block_time": 1234567890
            }
        }
        
        # Split into chunks
        serialized_data = json.dumps(state_data).encode('utf-8')
        chunk_size = len(serialized_data) // 2
        
        chunk_0 = serialized_data[:chunk_size]
        chunk_1 = serialized_data[chunk_size:]
        
        with open(temp_dir / "chunk_0000", 'wb') as f:
            f.write(chunk_0)
        
        with open(temp_dir / "chunk_0001", 'wb') as f:
            f.write(chunk_1)
        
        # Finalize restoration
        success = snapshot_manager.finalize_snapshot_restore(2)
        assert success == True
        
        # Verify state was applied
        mock_client.raw_driver.set.assert_called()
        mock_client.raw_driver.hard_apply.assert_called_with("1234567890")
        
        # Verify temp directory was cleaned up
        assert not temp_dir.exists()


class TestStateSync:
    """Test the ABCI state sync methods"""
    
    @pytest.fixture
    def mock_xian_app(self):
        """Mock Xian ABCI application"""
        app = Mock()
        app.cometbft_config = {"home": "/tmp/xian"}
        app.client = Mock()
        app.nonce_storage = Mock()
        app.snapshot_manager = None
        return app
    
    @pytest.mark.asyncio
    async def test_list_snapshots_empty(self, mock_xian_app):
        """Test listing snapshots when none exist"""
        from xian.methods.state_sync import list_snapshots
        
        req = Mock()
        response = await list_snapshots(mock_xian_app, req)
        
        assert isinstance(response, ResponseListSnapshots)
        assert len(response.snapshots) == 0
    
    @pytest.mark.asyncio
    async def test_offer_snapshot_accept(self, mock_xian_app):
        """Test accepting a snapshot offer"""
        from xian.methods.state_sync import offer_snapshot
        
        req = Mock()
        req.snapshot = Mock()
        req.snapshot.height = 1000
        req.snapshot.format = 1
        req.snapshot.chunks = 5
        req.app_hash = b"test_hash"
        
        response = await offer_snapshot(mock_xian_app, req)
        
        assert isinstance(response, ResponseOfferSnapshot)
        assert response.result == ResponseOfferSnapshot.Result.ACCEPT
    
    @pytest.mark.asyncio
    async def test_offer_snapshot_reject_format(self, mock_xian_app):
        """Test rejecting snapshot with unsupported format"""
        from xian.methods.state_sync import offer_snapshot
        
        req = Mock()
        req.snapshot = Mock()
        req.snapshot.format = 999  # Unsupported format
        req.app_hash = b"test_hash"
        
        response = await offer_snapshot(mock_xian_app, req)
        
        assert isinstance(response, ResponseOfferSnapshot)
        assert response.result == ResponseOfferSnapshot.Result.REJECT_FORMAT
    
    @pytest.mark.asyncio
    async def test_load_snapshot_chunk_not_found(self, mock_xian_app):
        """Test loading non-existent snapshot chunk"""
        from xian.methods.state_sync import load_snapshot_chunk
        
        req = Mock()
        req.height = 1000
        req.format = 1
        req.chunk = 0
        
        response = await load_snapshot_chunk(mock_xian_app, req)
        
        assert isinstance(response, ResponseLoadSnapshotChunk)
        assert response.chunk == b""
    
    @pytest.mark.asyncio
    async def test_apply_snapshot_chunk_success(self, mock_xian_app):
        """Test successful snapshot chunk application"""
        from xian.methods.state_sync import apply_snapshot_chunk
        
        req = Mock()
        req.index = 0
        req.chunk = b"test chunk data"
        req.sender = "peer123"
        
        response = await apply_snapshot_chunk(mock_xian_app, req)
        
        assert isinstance(response, ResponseApplySnapshotChunk)
        assert response.result == ResponseApplySnapshotChunk.Result.ACCEPT


if __name__ == "__main__":
    pytest.main([__file__])