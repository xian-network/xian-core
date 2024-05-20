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
)
from cometbft.abci.v1beta1.types_pb2 import (
    RequestQuery,
    ResponseQuery,
)

from cometbft.types.v1.params_pb2 import ConsensusParams
from cometbft.crypto.v1.keys_pb2 import PublicKey

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

class TestXianHandler(unittest.TestCase):

    def setUp(self):
        self.app = Xian()
        self.app.current_block_meta = {"height": 0, "nanos": 0}
        self.app.client.raw_driver.set("currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6", "123.45")
        self.handler = ProtocolHandler(self.app)

    def process_request(self, request_type, req):
        raw = self.handler.process(request_type, req)
        resp = deserialize(raw)
        return resp

    def test_get_query(self):
        request = Request(query=RequestQuery(path="/get/currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"))
        response = self.process_request("query", request)
        self.assertEqual(response.query.code, OkCode)
        self.assertEqual(response.query.info, "str")
        self.assertEqual(response.query.key, b"currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6")
        self.assertEqual(response.query.value, b"123.45")
        

if __name__ == "__main__":
    unittest.main()