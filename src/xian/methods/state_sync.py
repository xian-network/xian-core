"""
State Sync methods for fast blockchain synchronization using CometBFT's native state sync.
This allows nodes to sync by applying state changes directly instead of replaying transactions.
"""
import json
import hashlib
import os
import gzip
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
logger = logging.getLogger(__name__)

from cometbft.abci.v1beta1.types_pb2 import (
    ResponseListSnapshots,
    ResponseOfferSnapshot,
    ResponseLoadSnapshotChunk,
    ResponseApplySnapshotChunk,
    Snapshot
)
from xian.utils.block import get_latest_block_height, get_latest_block_hash
from contracting.storage.encoder import convert_dict


class StateSnapshotManager:
    """Manages state snapshots for fast sync"""
    
    def __init__(self, storage_home, client, nonce_storage):
        self.storage_home = Path(storage_home)
        self.client = client
        self.nonce_storage = nonce_storage
        self.snapshots_dir = self.storage_home / "snapshots"
        self.snapshots_dir.mkdir(exist_ok=True, parents=True)
        
        # Snapshot configuration
        self.chunk_size = 10 * 1024 * 1024  # 10MB chunks
        self.snapshot_interval = 1000  # Create snapshot every 1000 blocks
        self.max_snapshots = 5  # Keep max 5 snapshots
        
    def should_create_snapshot(self, height: int) -> bool:
        """Check if we should create a snapshot at this height"""
        return height % self.snapshot_interval == 0
    
    def create_snapshot(self, height: int, app_hash: bytes, block_time: int) -> Optional[str]:
        """Create a state snapshot at the given height"""
        try:
            logger.info(f"Creating state snapshot at height {height}")
            
            # Collect all state data
            state_data = self._collect_state_data()
            
            # Create snapshot metadata
            snapshot_id = f"{height}_{app_hash.hex()[:16]}"
            snapshot_path = self.snapshots_dir / f"snapshot_{snapshot_id}"
            snapshot_path.mkdir(exist_ok=True)
            
            # Save state data in chunks
            chunks = self._create_chunks(state_data)
            chunk_hashes = []
            
            for i, chunk_data in enumerate(chunks):
                chunk_file = snapshot_path / f"chunk_{i:04d}.gz"
                with gzip.open(chunk_file, 'wb') as f:
                    f.write(chunk_data)
                
                # Calculate chunk hash for verification
                chunk_hash = hashlib.sha256(chunk_data).hexdigest()
                chunk_hashes.append(chunk_hash)
            
            # Create snapshot metadata
            metadata = {
                "height": height,
                "app_hash": app_hash.hex(),
                "block_time": block_time,
                "chunks": len(chunks),
                "chunk_hashes": chunk_hashes,
                "format": 1,  # Snapshot format version
                "created_at": block_time
            }
            
            # Save metadata
            metadata_file = snapshot_path / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Created snapshot {snapshot_id} with {len(chunks)} chunks")
            
            # Cleanup old snapshots
            self._cleanup_old_snapshots()
            
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Failed to create snapshot at height {height}: {e}")
            return None
    
    def _collect_state_data(self) -> Dict[str, Any]:
        """Collect all current state data"""
        state_data = {
            "contract_state": {},
            "nonces": {},
            "metadata": {
                "height": get_latest_block_height(),
                "app_hash": get_latest_block_hash().hex()
            }
        }
        
        # Collect contract state
        try:
            contract_files = self.client.raw_driver.get_contract_files()
            
            for contract_file in contract_files:
                # Get all items for this contract using the contract name as prefix
                contract_data = self.client.raw_driver.items(contract_name)
                if contract_data:
                    state_data["contract_state"][contract_name] = dict(contract_data)
            
            # Also collect any other state that doesn't follow the contract.d pattern
            # by getting all items without a prefix
            all_items = self.client.raw_driver.items("")
            if all_items:
                # Filter out items already captured in contract_state
                remaining_items = {}
                for key, value in all_items.items():
                    # Check if this key belongs to any of the contracts we already processed
                    belongs_to_contract = False
                    for contract_name in state_data["contract_state"].keys():
                        if key.startswith(contract_name + "."):
                            belongs_to_contract = True
                            break
                    
                    if not belongs_to_contract:
                        remaining_items[key] = value
                
                if remaining_items:
                    state_data["contract_state"]["_global"] = remaining_items
            
            # Collect nonces - they are stored with keys like "__n:sender."
            try:
                from xian.constants import Constants as c
                from contracting import constants as config
                
                # Get all nonce keys
                nonce_prefix = c.NONCE_FILENAME + config.INDEX_SEPARATOR
                nonce_items = self.client.raw_driver.items(nonce_prefix)
                
                # Extract sender from nonce keys and build nonces dict
                nonces = {}
                for key, value in nonce_items.items():
                    if key.startswith(nonce_prefix):
                        # Extract sender from key like "__n:sender."
                        sender_part = key[len(nonce_prefix):]
                        if sender_part.endswith(config.DELIMITER):
                            sender = sender_part[:-len(config.DELIMITER)]
                            nonces[sender] = value
                
                state_data["nonces"] = nonces
                
                # Also collect pending nonces if they exist
                pending_nonce_prefix = c.PENDING_NONCE_FILENAME + config.INDEX_SEPARATOR
                pending_nonce_items = self.client.raw_driver.items(pending_nonce_prefix)
                
                if pending_nonce_items:
                    pending_nonces = {}
                    for key, value in pending_nonce_items.items():
                        if key.startswith(pending_nonce_prefix):
                            sender_part = key[len(pending_nonce_prefix):]
                            if sender_part.endswith(config.DELIMITER):
                                sender = sender_part[:-len(config.DELIMITER)]
                                pending_nonces[sender] = value
                    
                    if pending_nonces:
                        state_data["pending_nonces"] = pending_nonces
                        
            except Exception as e:
                logger.warning(f"Could not collect nonces: {e}")
            
        except Exception as e:
            logger.error(f"Error collecting state data: {e}")
        
        return state_data
    
    def _create_chunks(self, state_data: Dict[str, Any]) -> List[bytes]:
        """Split state data into chunks"""
        # Serialize state data
        serialized_data = json.dumps(state_data, default=str).encode('utf-8')
        
        # Split into chunks
        chunks = []
        for i in range(0, len(serialized_data), self.chunk_size):
            chunk = serialized_data[i:i + self.chunk_size]
            chunks.append(chunk)
        
        return chunks
    
    def _cleanup_old_snapshots(self):
        """Remove old snapshots to save disk space"""
        try:
            snapshots = []
            for item in self.snapshots_dir.iterdir():
                if item.is_dir() and item.name.startswith("snapshot_"):
                    metadata_file = item / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        snapshots.append((metadata["height"], item))
            
            # Sort by height and keep only the latest ones
            snapshots.sort(key=lambda x: x[0], reverse=True)
            
            for height, snapshot_path in snapshots[self.max_snapshots:]:
                logger.info(f"Removing old snapshot at height {height}")
                import shutil
                shutil.rmtree(snapshot_path)
                
        except Exception as e:
            logger.error(f"Error cleaning up old snapshots: {e}")
    
    def list_available_snapshots(self) -> List[Snapshot]:
        """List all available snapshots"""
        snapshots = []
        
        try:
            for item in self.snapshots_dir.iterdir():
                if item.is_dir() and item.name.startswith("snapshot_"):
                    metadata_file = item / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        
                        snapshot = Snapshot(
                            height=metadata["height"],
                            format=metadata["format"],
                            chunks=metadata["chunks"],
                            hash=bytes.fromhex(metadata["app_hash"]),
                            metadata=json.dumps(metadata).encode('utf-8')
                        )
                        snapshots.append(snapshot)
        
        except Exception as e:
            logger.error(f"Error listing snapshots: {e}")
        
        return sorted(snapshots, key=lambda s: s.height, reverse=True)
    
    def load_snapshot_chunk(self, height: int, format: int, chunk_index: int) -> Optional[bytes]:
        """Load a specific chunk from a snapshot"""
        try:
            # Find the snapshot
            snapshot_id = None
            for item in self.snapshots_dir.iterdir():
                if item.is_dir() and item.name.startswith("snapshot_"):
                    metadata_file = item / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        if metadata["height"] == height and metadata["format"] == format:
                            snapshot_id = item.name
                            break
            
            if not snapshot_id:
                logger.error(f"Snapshot not found for height {height}, format {format}")
                return None
            
            # Load the specific chunk
            snapshot_path = self.snapshots_dir / snapshot_id
            chunk_file = snapshot_path / f"chunk_{chunk_index:04d}.gz"
            
            if not chunk_file.exists():
                logger.error(f"Chunk {chunk_index} not found for snapshot {snapshot_id}")
                return None
            
            with gzip.open(chunk_file, 'rb') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Error loading snapshot chunk: {e}")
            return None
    
    def apply_snapshot_chunk(self, chunk_index: int, chunk_data: bytes) -> bool:
        """Apply a snapshot chunk to restore state"""
        try:
            # For now, we'll store chunks temporarily and apply when complete
            temp_dir = self.snapshots_dir / "temp_restore"
            temp_dir.mkdir(exist_ok=True)
            
            chunk_file = temp_dir / f"chunk_{chunk_index:04d}"
            with open(chunk_file, 'wb') as f:
                f.write(chunk_data)
            
            logger.debug(f"Stored chunk {chunk_index} for restoration")
            return True
            
        except Exception as e:
            logger.error(f"Error applying snapshot chunk {chunk_index}: {e}")
            return False
    
    def finalize_snapshot_restore(self, total_chunks: int) -> bool:
        """Finalize snapshot restoration by applying all chunks"""
        try:
            temp_dir = self.snapshots_dir / "temp_restore"
            
            # Reconstruct the full state data
            full_data = b""
            for i in range(total_chunks):
                chunk_file = temp_dir / f"chunk_{i:04d}"
                if not chunk_file.exists():
                    logger.error(f"Missing chunk {i} during restoration")
                    return False
                
                with open(chunk_file, 'rb') as f:
                    full_data += f.read()
            
            # Deserialize state data
            state_data = json.loads(full_data.decode('utf-8'))
            
            # Apply state to storage
            self._apply_state_data(state_data)
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info("Successfully restored state from snapshot")
            return True
            
        except Exception as e:
            logger.error(f"Error finalizing snapshot restore: {e}")
            return False
    
    def _apply_state_data(self, state_data: Dict[str, Any]):
        """Apply state data to the storage"""
        try:
            # Apply contract state
            for contract_name, contract_data in state_data.get("contract_state", {}).items():
                for key, value in contract_data.items():
                    # Convert dict values if needed
                    if isinstance(value, dict):
                        value = convert_dict(value)
                    
                    # Apply to storage
                    full_key = f"{contract_name}.{key}" if not key.startswith(contract_name) else key
                    self.client.raw_driver.set(full_key, value)
            
            # Apply nonces
            for nonce_key, nonce_value in state_data.get("nonces", {}).items():
                self.nonce_storage.set_nonce(nonce_key, nonce_value)
            
            # Apply pending nonces if they exist
            pending_nonces = state_data.get("pending_nonces", {})
            for sender, nonce in pending_nonces.items():
                from xian.constants import Constants as c
                from contracting import constants as config
                self.client.raw_driver.set(
                    c.PENDING_NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER,
                    nonce
                )
            
            # Commit changes
            metadata = state_data.get("metadata", {})
            block_time = metadata.get("block_time", "0")
            self.client.raw_driver.hard_apply(str(block_time))
            
        except Exception as e:
            logger.error(f"Error applying state data: {e}")
            raise


async def list_snapshots(self, req) -> ResponseListSnapshots:
    """List available snapshots for state sync"""
    try:
        if not hasattr(self, 'snapshot_manager'):
            self.snapshot_manager = StateSnapshotManager(
                self.cometbft_config.get("home", "/tmp/xian"),
                self.client,
                self.nonce_storage
            )
        
        snapshots = self.snapshot_manager.list_available_snapshots()
        
        logger.info(f"Listing {len(snapshots)} available snapshots")
        return ResponseListSnapshots(snapshots=snapshots)
        
    except Exception as e:
        logger.error(f"Error listing snapshots: {e}")
        return ResponseListSnapshots(snapshots=[])


async def offer_snapshot(self, req) -> ResponseOfferSnapshot:
    """Handle snapshot offer during state sync"""
    try:
        snapshot = req.snapshot
        app_hash = req.app_hash
        
        logger.info(f"Offered snapshot: height={snapshot.height}, format={snapshot.format}, chunks={snapshot.chunks}")
        
        # Basic validation
        if snapshot.format != 1:
            logger.warning(f"Unsupported snapshot format: {snapshot.format}")
            return ResponseOfferSnapshot(result=ResponseOfferSnapshot.Result.REJECT_FORMAT)
        
        if len(app_hash) == 0:
            logger.warning("No app hash provided with snapshot")
            return ResponseOfferSnapshot(result=ResponseOfferSnapshot.Result.REJECT)
        
        # Initialize snapshot manager if needed
        if not hasattr(self, 'snapshot_manager'):
            self.snapshot_manager = StateSnapshotManager(
                self.cometbft_config.get("home", "/tmp/xian"),
                self.client,
                self.nonce_storage
            )
        
        # Accept the snapshot
        logger.info("Accepting snapshot for restoration")
        return ResponseOfferSnapshot(result=ResponseOfferSnapshot.Result.ACCEPT)
        
    except Exception as e:
        logger.error(f"Error handling snapshot offer: {e}")
        return ResponseOfferSnapshot(result=ResponseOfferSnapshot.Result.ABORT)


async def load_snapshot_chunk(self, req) -> ResponseLoadSnapshotChunk:
    """Load a snapshot chunk for state sync"""
    try:
        height = req.height
        format = req.format
        chunk_index = req.chunk
        
        logger.debug(f"Loading snapshot chunk: height={height}, format={format}, chunk={chunk_index}")
        
        if not hasattr(self, 'snapshot_manager'):
            self.snapshot_manager = StateSnapshotManager(
                self.cometbft_config.get("home", "/tmp/xian"),
                self.client,
                self.nonce_storage
            )
        
        chunk_data = self.snapshot_manager.load_snapshot_chunk(height, format, chunk_index)
        
        if chunk_data is None:
            logger.error(f"Failed to load chunk {chunk_index}")
            return ResponseLoadSnapshotChunk(chunk=b"")
        
        logger.debug(f"Loaded chunk {chunk_index}, size: {len(chunk_data)} bytes")
        return ResponseLoadSnapshotChunk(chunk=chunk_data)
        
    except Exception as e:
        logger.error(f"Error loading snapshot chunk: {e}")
        return ResponseLoadSnapshotChunk(chunk=b"")


async def apply_snapshot_chunk(self, req) -> ResponseApplySnapshotChunk:
    """Apply a snapshot chunk during state sync"""
    try:
        chunk_index = req.index
        chunk_data = req.chunk
        sender = req.sender
        
        logger.debug(f"Applying snapshot chunk {chunk_index}, size: {len(chunk_data)} bytes, from: {sender}")
        
        if not hasattr(self, 'snapshot_manager'):
            self.snapshot_manager = StateSnapshotManager(
                self.cometbft_config.get("home", "/tmp/xian"),
                self.client,
                self.nonce_storage
            )
        
        success = self.snapshot_manager.apply_snapshot_chunk(chunk_index, chunk_data)
        
        if not success:
            logger.error(f"Failed to apply chunk {chunk_index}")
            return ResponseApplySnapshotChunk(result=ResponseApplySnapshotChunk.Result.RETRY)
        
        logger.debug(f"Successfully applied chunk {chunk_index}")
        return ResponseApplySnapshotChunk(result=ResponseApplySnapshotChunk.Result.ACCEPT)
        
    except Exception as e:
        logger.error(f"Error applying snapshot chunk: {e}")
        return ResponseApplySnapshotChunk(result=ResponseApplySnapshotChunk.Result.ABORT)
