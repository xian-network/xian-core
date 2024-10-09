from cometbft.abci.v1beta1.types_pb2 import ResponseInfo
from xian.utils.block import (
    get_latest_block_hash,
    get_latest_block_height,
)


async def info(self, req) -> ResponseInfo:
    res = ResponseInfo()
    res.app_version = self.app_version
    res.version = req.version
    res.last_block_height = get_latest_block_height()
    res.last_block_app_hash = get_latest_block_hash()
    return res
