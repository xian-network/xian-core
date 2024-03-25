from cometbft.abci.v1beta3.types_pb2 import ResponseCommit
from xian.driver_api import (
    set_latest_block_hash,
    set_latest_block_height
)

def commit(self) -> ResponseCommit:
    # commit block to filesystem db
    set_latest_block_hash(self.fingerprint_hash, self.driver)
    set_latest_block_height(self.current_block_meta["height"], self.driver)

    self.driver.hard_apply(str(self.current_block_meta["nanos"]))

    # unset current_block_meta & cleanup
    self.current_block_meta = None
    self.fingerprint_hashes = []
    self.fingerprint_hash = None
    self.current_block_rewards = {}

    retain_height = 0 
    if self.pruning_enabled:
        if self.current_block_meta["height"] > self.blocks_to_keep:
            retain_height = self.current_block_meta["height"] - self.blocks_to_keep

    return ResponseCommit(retain_height=retain_height)
