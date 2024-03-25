from cometbft.abci.v1beta1.types_pb2 import ResponseInfo
from xian.driver_api import (
    get_latest_block_hash,
    get_latest_block_height,
)

def info(self, req) -> ResponseInfo:
    res = ResponseInfo()
    res.app_version = self.app_version
    res.version = req.version
    res.last_block_height = get_latest_block_height(self.driver)
    res.last_block_app_hash = get_latest_block_hash(self.driver)
    return res