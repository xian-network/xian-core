import os
import unittest
from io import BytesIO
import logging
import asyncio

from xian.xian_abci import Xian
from abci.server import ProtocolHandler
from abci.utils import read_messages
from fixtures.test_constants import TestConstants

from cometbft.abci.v1beta3.types_pb2 import (
    Request,
    Response,
)

from cometbft.abci.v1beta2.types_pb2 import (
    RequestInfo,
)

from cometbft.abci.v1beta1.types_pb2 import ResponseInfo, RequestCommit



# Disable any kind of logging
logging.disable(logging.CRITICAL)

async def deserialize(raw: bytes) -> Response:
    try:
        resp = next(read_messages(BytesIO(raw), Response))
        return resp
    except Exception as e:
        logging.error("Deserialization error: %s", e)
        raise

class TestInfo(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.app = await Xian.create(constants=TestConstants)
        self.app.current_block_meta = {"height": 0, "nanos": 0}
        self.handler = ProtocolHandler(self.app)
        self.app.merkle_root_hash = b''

    async def process_request(self, request_type, req):
        raw = await self.handler.process(request_type, req)
        resp = await deserialize(raw)
        return resp

    async def test_info(self):
        commit_request = Request(commit=RequestCommit())
        await self.process_request("commit", commit_request)
        request = Request(info=RequestInfo())
        response = await self.process_request("info", request)
        self.assertEqual(response.info.app_version, 1)
        self.assertEqual(response.info.data, "")  # We don't use that
        self.assertEqual(response.info.version, "")  # Not running CometBFT
        self.assertEqual(response.info.last_block_height, 0)
        self.assertEqual(response.info.last_block_app_hash, b"")

if __name__ == "__main__":
    unittest.main()
