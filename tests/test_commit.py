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

from fixtures.test_constants import TestConstants

# Disable any kind of logging
logging.disable(logging.CRITICAL)

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

async def deserialize(raw: bytes) -> Response:
    try:
        resp = next(read_messages(BytesIO(raw), Response))
        return resp
    except Exception as e:
        logging.error("Deserialization error: %s", e)
        raise

class TestCommit(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.app = Xian(constants=TestConstants)
        self.app.current_block_meta = {"height": 0, "nanos": 0}
        self.handler = ProtocolHandler(self.app)

    async def process_request(self, request_type, req):
        raw = await self.handler.process(request_type, req)
        resp = await deserialize(raw)
        return resp

    async def test_commit(self):
        request = Request(commit=RequestCommit())
        response = await self.process_request("commit", request)
        self.assertEqual(response.commit.retain_height, 0)

if __name__ == "__main__":
    unittest.main()
