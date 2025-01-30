import os
import unittest
from io import BytesIO
import logging
import asyncio

from xian.xian_abci import Xian
from abci.server import ProtocolHandler
from abci.utils import read_messages

from cometbft.abci.v1beta3.types_pb2 import (
    Request,
    Response,
    ResponseCommit,
)
from cometbft.abci.v1beta1.types_pb2 import (
    RequestCommit,
)

from fixtures.mock_constants import MockConstants
from utils import setup_fixtures, teardown_fixtures
# Disable any kind of logging
logging.disable(logging.CRITICAL)

async def deserialize(raw: bytes) -> Response:
    try:
        resp = next(read_messages(BytesIO(raw), Response))
        return resp
    except Exception as e:
        logging.error("Deserialization error: %s", e)
        raise

class TestCommit(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        setup_fixtures()
        self.app = await Xian.create(constants=MockConstants)
        self.app.current_block_meta = {"height": 0, "nanos": 0}
        self.app.merkle_root_hash = b'abc123'
        self.app.chain_id = "xian-testnet-1"
        self.app.fingerprint_hashes = []
        self.app.current_block_rewards = {}
        self.handler = ProtocolHandler(self.app)
        
    async def asyncTearDown(self):
        teardown_fixtures()


    async def process_request(self, request_type, req):
        raw = await self.handler.process(request_type, req)
        resp = await deserialize(raw)
        return resp

    async def test_commit(self):
        # breakpoint()
        request = Request(commit=RequestCommit())
        response = await self.process_request("commit", request)
        self.assertEqual(response.commit.retain_height, 0)

if __name__ == "__main__":
    unittest.main()
