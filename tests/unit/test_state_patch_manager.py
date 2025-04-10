import unittest
import json
import os
import tempfile
from pathlib import Path
import shutil

from unittest.mock import MagicMock, patch
from xian.utils.state_patches import StatePatchManager, hash_from_state_changes


class TestStatePatchManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_patches_file = self.test_dir / "test_patches.json"
        
        self.test_patches = {
            "100": [
                {
                    "key": "test.key1",
                    "value": "value1",
                    "comment": "Test comment 1"
                }
            ],
            "200": [
                {
                    "key": "test.key2",
                    "value": 123,
                    "comment": "Test comment 2"
                },
                {
                    "key": "test.key3",
                    "value": {"nested": "value"},
                    "comment": "Test comment 3"
                }
            ]
        }
        
        with open(self.test_patches_file, "w") as f:
            json.dump(self.test_patches, f)
            
        # Create a mock raw_driver
        self.mock_driver = MagicMock()
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
        
    def test_load_patches(self):
        """Test loading patches from file"""
        manager = StatePatchManager(self.mock_driver)
        manager.load_patches(self.test_patches_file)
        
        # Verify patches were loaded correctly
        self.assertTrue(manager.loaded)
        self.assertEqual(len(manager.patches), 2)
        self.assertIn(100, manager.patches)
        self.assertIn(200, manager.patches)
        
        # Verify patch content
        self.assertEqual(len(manager.patches[100]), 1)
        self.assertEqual(len(manager.patches[200]), 2)
        self.assertEqual(manager.patches[100][0]["key"], "test.key1")
        self.assertEqual(manager.patches[200][0]["value"], 123)
        
    def test_load_nonexistent_file(self):
        """Test loading a non-existent file"""
        manager = StatePatchManager(self.mock_driver)
        nonexistent_file = self.test_dir / "nonexistent.json"
        
        manager.load_patches(nonexistent_file)
        
        # Should still be marked as loaded but with empty patches
        self.assertTrue(manager.loaded)
        self.assertEqual(len(manager.patches), 0)
        
    def test_load_invalid_json(self):
        """Test loading an invalid JSON file"""
        invalid_json_file = self.test_dir / "invalid.json"
        
        with open(invalid_json_file, "w") as f:
            f.write("This is not valid JSON")
            
        manager = StatePatchManager(self.mock_driver)
        manager.load_patches(invalid_json_file)
        
        # Should not be marked as loaded due to error
        self.assertFalse(manager.loaded)
        self.assertEqual(len(manager.patches), 0)
        
    def test_apply_patches_for_block(self):
        """Test applying patches for a specific block"""
        manager = StatePatchManager(self.mock_driver)
        manager.load_patches(self.test_patches_file)
        
        # Apply patches for block 100
        patch_hash = manager.apply_patches_for_block(100, 123456)
        
        # Verify driver.set was called correctly
        self.mock_driver.set.assert_called_with("test.key1", "value1")
        
        # Verify hard_apply was called
        self.mock_driver.hard_apply.assert_called_with(123456)
        
        # Verify patch hash was returned
        self.assertIsNotNone(patch_hash)
        
    def test_apply_patches_multiple_keys(self):
        """Test applying multiple patches for a block"""
        manager = StatePatchManager(self.mock_driver)
        manager.load_patches(self.test_patches_file)
        
        # Apply patches for block 200 (has 2 patches)
        manager.apply_patches_for_block(200, 123456)
        
        # Verify driver.set was called correctly for both keys
        self.assertEqual(self.mock_driver.set.call_count, 2)
        self.mock_driver.set.assert_any_call("test.key2", 123)
        self.mock_driver.set.assert_any_call("test.key3", {"nested": "value"})
        
    def test_apply_patches_nonexistent_block(self):
        """Test applying patches for a block that doesn't have any"""
        manager = StatePatchManager(self.mock_driver)
        manager.load_patches(self.test_patches_file)
        
        # Try to apply patches for block 300 (doesn't exist)
        result, applied_patches = manager.apply_patches_for_block(300, 123456)
        
        # Should return None for patch_hash and empty list for applied_patches
        self.assertIsNone(result)
        self.assertEqual(applied_patches, [])
        self.mock_driver.set.assert_not_called()
        self.mock_driver.hard_apply.assert_not_called()
        
    def test_hash_from_state_changes(self):
        """Test the hash generation from state changes"""
        # Simple state changes
        changes1 = [
            {"key": "test.key1", "value": "value1", "comment": "comment1"}
        ]
        
        # Same content but different comment (should result in same hash)
        changes2 = [
            {"key": "test.key1", "value": "value1", "comment": "different comment"}
        ]
        
        # Different content (should result in different hash)
        changes3 = [
            {"key": "test.key1", "value": "different_value", "comment": "comment1"}
        ]
        
        # Test that comment doesn't affect hash
        hash1 = hash_from_state_changes(changes1)
        hash2 = hash_from_state_changes(changes2)
        self.assertEqual(hash1, hash2, "Comments should not affect the hash")
        
        # Test that different values produce different hashes
        hash3 = hash_from_state_changes(changes3)
        self.assertNotEqual(hash1, hash3, "Different values should produce different hashes")
        
    def test_hash_deterministic_ordering(self):
        """Test that hash generation is deterministic regardless of order"""
        # Changes in one order
        changes1 = [
            {"key": "test.key1", "value": "value1"},
            {"key": "test.key2", "value": "value2"}
        ]
        
        # Same changes in different order
        changes2 = [
            {"key": "test.key2", "value": "value2"},
            {"key": "test.key1", "value": "value1"}
        ]
        
        # Hashes should be identical regardless of order
        hash1 = hash_from_state_changes(changes1)
        hash2 = hash_from_state_changes(changes2)
        self.assertEqual(hash1, hash2, "Hash should be deterministic regardless of order")
        
if __name__ == "__main__":
    unittest.main() 