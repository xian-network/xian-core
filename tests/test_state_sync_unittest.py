"""
Tests for State Sync functionality using unittest
"""
import unittest
import tempfile
import json
import gzip
from pathlib import Path
from unittest.mock import Mock, patch

from xian.methods.state_sync import StateSnapshotManager


class TestStateSnapshotManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary storage directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_storage = Path(self.temp_dir.name)
        
        # Mock contracting client
        self.mock_client = Mock()
        self.mock_client.raw_driver = Mock()
        self.mock_client.raw_driver.get_contract_files.return_value = ['currency.d', 'masternodes.d']
        self.mock_client.raw_driver.items.return_value = {
            'currency.balances:alice': 1000,
            'currency.balances:bob': 500,
            'masternodes.nodes': ['node1', 'node2']
        }
        self.mock_client.raw_driver.set = Mock()
        self.mock_client.raw_driver.hard_apply = Mock()
        
        # Mock nonce storage
        self.mock_nonce_storage = Mock()
        self.mock_nonce_storage.set_nonce = Mock()
        
        # Create StateSnapshotManager instance
        self.snapshot_manager = StateSnapshotManager(
            self.temp_storage, 
            self.mock_client, 
            self.mock_nonce_storage
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()
    
    def test_should_create_snapshot(self):
        """Test snapshot creation interval logic"""
        # Should create at interval blocks
        self.assertTrue(self.snapshot_manager.should_create_snapshot(1000))
        self.assertTrue(self.snapshot_manager.should_create_snapshot(2000))
        
        # Should not create at non-interval blocks
        self.assertFalse(self.snapshot_manager.should_create_snapshot(999))
        self.assertFalse(self.snapshot_manager.should_create_snapshot(1001))
        self.assertFalse(self.snapshot_manager.should_create_snapshot(1500))
    
    @patch('xian.methods.state_sync.get_latest_block_height')
    @patch('xian.methods.state_sync.get_latest_block_hash')
    def test_collect_state_data(self, mock_get_hash, mock_get_height):
        """Test state data collection"""
        # Mock block info
        mock_get_height.return_value = 1000
        mock_get_hash.return_value = b'test_hash'
        
        # Mock items method to return different data for different prefixes
        def mock_items(prefix):
            if prefix == "currency":
                return {'currency.balances:alice': 1000, 'currency.balances:bob': 500}
            elif prefix == "masternodes":
                return {'masternodes.nodes': ['node1', 'node2']}
            elif prefix == "__n:":  # nonce prefix
                return {'__n:alice.': 1, '__n:bob.': 2}
            elif prefix == "":  # all items
                return {
                    'currency.balances:alice': 1000,
                    'currency.balances:bob': 500,
                    'masternodes.nodes': ['node1', 'node2'],
                    '__n:alice.': 1,
                    '__n:bob.': 2
                }
            return {}
        
        self.mock_client.raw_driver.items.side_effect = mock_items
        
        # Collect state data
        state_data = self.snapshot_manager._collect_state_data()
        
        # Verify structure
        self.assertIn('contract_state', state_data)
        self.assertIn('nonces', state_data)
        self.assertIn('metadata', state_data)
        
        # Verify metadata
        self.assertEqual(state_data['metadata']['height'], 1000)
        self.assertEqual(state_data['metadata']['app_hash'], 'test_hash')
        
        # Verify contract state
        self.assertIn('currency', state_data['contract_state'])
        self.assertIn('masternodes', state_data['contract_state'])
        
        # Verify nonces
        self.assertEqual(state_data['nonces']['alice'], 1)
        self.assertEqual(state_data['nonces']['bob'], 2)
    
    def test_create_chunks(self):
        """Test chunk creation"""
        # Create test state data
        state_data = {
            'contract_state': {
                'currency': {'balances:alice': 1000}
            },
            'nonces': {'alice': 1},
            'metadata': {'height': 1000}
        }
        
        # Create chunks
        chunks = self.snapshot_manager._create_chunks(state_data)
        
        # Verify chunks
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)
        
        # Verify chunks are compressed
        for chunk in chunks:
            self.assertIsInstance(chunk, bytes)
            # Should be able to decompress
            decompressed = gzip.decompress(chunk)
            self.assertIsInstance(decompressed, bytes)
    
    @patch('xian.methods.state_sync.get_latest_block_height')
    @patch('xian.methods.state_sync.get_latest_block_hash')
    def test_create_snapshot(self, mock_get_hash, mock_get_height):
        """Test snapshot creation"""
        # Mock block info
        mock_get_height.return_value = 1000
        mock_get_hash.return_value = b'test_hash'
        
        # Mock state data collection
        def mock_items(prefix):
            if prefix == "currency":
                return {'currency.balances:alice': 1000}
            elif prefix == "__n:":
                return {'__n:alice.': 1}
            elif prefix == "":
                return {'currency.balances:alice': 1000, '__n:alice.': 1}
            return {}
        
        self.mock_client.raw_driver.items.side_effect = mock_items
        
        # Create snapshot
        snapshot_id = self.snapshot_manager.create_snapshot(1000, b'test_hash', 1234567890)
        
        # Verify snapshot was created
        self.assertIsNotNone(snapshot_id)
        self.assertIsInstance(snapshot_id, str)
        
        # Verify snapshot directory exists
        snapshot_dir = self.temp_storage / "snapshots" / snapshot_id
        self.assertTrue(snapshot_dir.exists())
        
        # Verify metadata file exists
        metadata_file = snapshot_dir / "metadata.json"
        self.assertTrue(metadata_file.exists())
        
        # Verify metadata content
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        self.assertEqual(metadata['height'], 1000)
        self.assertEqual(metadata['format'], 1)
        self.assertIn('chunks', metadata)
        self.assertGreater(metadata['chunks'], 0)
    
    def test_list_available_snapshots(self):
        """Test listing available snapshots"""
        # Initially no snapshots
        snapshots = self.snapshot_manager.list_available_snapshots()
        self.assertEqual(len(snapshots), 0)
        
        # Create a mock snapshot directory
        snapshot_dir = self.temp_storage / "snapshots" / "test_snapshot"
        snapshot_dir.mkdir(parents=True)
        
        # Create metadata file
        metadata = {
            'height': 1000,
            'format': 1,
            'chunks': 2,
            'app_hash': 'test_hash',
            'block_time': 1234567890
        }
        
        with open(snapshot_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f)
        
        # List snapshots
        snapshots = self.snapshot_manager.list_available_snapshots()
        self.assertEqual(len(snapshots), 1)
        
        snapshot = snapshots[0]
        self.assertEqual(snapshot.height, 1000)
        self.assertEqual(snapshot.format, 1)
        self.assertEqual(snapshot.chunks, 2)
    
    def test_load_snapshot_chunk(self):
        """Test loading snapshot chunks"""
        # Create a mock snapshot with chunks
        snapshot_dir = self.temp_storage / "snapshots" / "test_snapshot"
        snapshot_dir.mkdir(parents=True)
        
        # Create test chunk
        test_data = b"test chunk data"
        chunk_file = snapshot_dir / "chunk_0.gz"
        with gzip.open(chunk_file, 'wb') as f:
            f.write(test_data)
        
        # Load chunk
        chunk_data = self.snapshot_manager.load_snapshot_chunk(1000, 1, 0)
        
        # Verify chunk data
        self.assertEqual(chunk_data, test_data)
    
    def test_apply_snapshot_chunk(self):
        """Test applying snapshot chunks"""
        # Create test chunk data
        chunk_data = {
            'contract_state': {
                'currency': {'balances:alice': 1000}
            },
            'nonces': {'alice': 1}
        }
        
        chunk_bytes = gzip.compress(json.dumps(chunk_data).encode())
        
        # Apply chunk
        success = self.snapshot_manager.apply_snapshot_chunk(0, chunk_bytes)
        
        # Verify success
        self.assertTrue(success)
        
        # Verify temp file was created
        temp_files = list((self.temp_storage / "temp_restore").glob("chunk_*.json"))
        self.assertEqual(len(temp_files), 1)
    
    def test_finalize_snapshot_restore(self):
        """Test finalizing snapshot restoration"""
        # Create temp chunk files
        temp_dir = self.temp_storage / "temp_restore"
        temp_dir.mkdir(parents=True)
        
        # Create test chunks
        chunk1 = {
            'contract_state': {
                'currency': {'balances:alice': 1000}
            },
            'nonces': {'alice': 1}
        }
        
        chunk2 = {
            'contract_state': {
                'masternodes': {'nodes': ['node1']}
            },
            'metadata': {'height': 1000, 'block_time': '1234567890'}
        }
        
        with open(temp_dir / "chunk_0.json", 'w') as f:
            json.dump(chunk1, f)
        
        with open(temp_dir / "chunk_1.json", 'w') as f:
            json.dump(chunk2, f)
        
        # Finalize restoration
        success = self.snapshot_manager.finalize_snapshot_restore(2)
        
        # Verify success
        self.assertTrue(success)
        
        # Verify driver methods were called
        self.mock_client.raw_driver.set.assert_called()
        self.mock_client.raw_driver.hard_apply.assert_called()
        self.mock_nonce_storage.set_nonce.assert_called()


if __name__ == '__main__':
    unittest.main()