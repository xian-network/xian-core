from cometbft.abci.v1beta3.types_pb2 import ResponseCommit
from xian.utils.block import (
    set_latest_block_hash,
    set_latest_block_height
)


async def commit(self) -> ResponseCommit:
    # commit block to filesystem db
    set_latest_block_hash(self.fingerprint_hash, self.client.raw_driver)
    set_latest_block_height(self.current_block_meta["height"], self.client.raw_driver)

    self.client.raw_driver.hard_apply(str(self.current_block_meta["nanos"]))

    # unset current_block_meta & cleanup
    self.fingerprint_hashes = []
    self.fingerprint_hash = None
    self.current_block_rewards = {}

    retain_height = 0 
    if self.pruning_enabled:
        if self.current_block_meta["height"] > self.blocks_to_keep:
            retain_height = self.current_block_meta["height"] - self.blocks_to_keep

    self.current_block_meta = None

    return ResponseCommit(retain_height=retain_height)
