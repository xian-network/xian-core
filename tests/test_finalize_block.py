import os
import unittest
from io import BytesIO
import logging

from xian.constants import OkCode, ErrorCode
from xian.xian_abci import Xian
from abci.server import ProtocolHandler
from abci.utils import read_messages

from cometbft.abci.v1beta3.types_pb2 import (
    Request,
    Response,
    ResponseFinalizeBlock,
    RequestFinalizeBlock,
)


# Disable any kind of logging
logging.disable(logging.CRITICAL)

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

def deserialize(raw: bytes) -> Response:
    try:
        resp = next(read_messages(BytesIO(raw), Response))
        return resp
    except Exception as e:
        logging.error("Deserialization error: %s", e)
        raise

class TestFinalizeBlock(unittest.TestCase):

    def setUp(self):
        self.app = Xian()
        self.handler = ProtocolHandler(self.app)

    def process_request(self, request_type, req):
        raw = self.handler.process(request_type, req)
        resp = deserialize(raw)
        return resp

    def test_finalize_block(self):
        request = Request(finalize_block=RequestFinalizeBlock()) # We should add a working transaction to the block
        response = self.process_request("finalize_block", request)
        self.assertEqual(response.finalize_block.app_hash, b"4c1326d058447b0c526d48698e9b0f5100c6f4d0785b3ec6491e9eb2c07b7580")

if __name__ == "__main__":
    unittest.main()