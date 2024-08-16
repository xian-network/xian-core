import os
import asyncio
import unittest
from io import BytesIO
import logging

from xian.xian_abci import Xian
from abci.server import ProtocolHandler
from abci.utils import read_messages

from cometbft.abci.v1beta3.types_pb2 import (
    Request,
    Response,
    RequestInitChain,
    ResponseInitChain,
    ResponseCheckTx,
    ResponseFinalizeBlock,
    RequestFinalizeBlock,
    ResponseCommit,
    RequestPrepareProposal,
    RequestProcessProposal,
)
from cometbft.abci.v1beta1.types_pb2 import (
    ResponseInfo,
    RequestQuery,
    ResponseQuery,
    RequestFlush,
    ResponseFlush,
    RequestEcho,
    ResponseEcho,
    RequestCheckTx,
    ValidatorUpdate,
    RequestCommit,
)
from cometbft.abci.v1beta2.types_pb2 import (
    ResponsePrepareProposal,
    ResponseProcessProposal,
    RequestInfo,
)
from cometbft.types.v1.params_pb2 import ConsensusParams
from cometbft.crypto.v1.keys_pb2 import PublicKey

from fixtures.test_constants import TestConstants

# Disable any kind of logging
logging.disable(logging.CRITICAL)

async def deserialize(raw: bytes) -> Response:
    try:
        resp = next(read_messages(BytesIO(raw), Response))
        return resp
    except Exception as e:
        logging.error("Deserialization error: %s", e)
        raise

class TestXianHandler(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.app = await Xian.create(constants=TestConstants)
        self.app.current_block_meta = {"height": 0, "nanos": 0}
        self.handler = ProtocolHandler(self.app)

    async def process_request(self, request_type, req):
        raw = await self.handler.process(request_type, req)
        resp = await deserialize(raw)
        return resp

    async def test_flush(self):
        req = Request(flush=RequestFlush())
        resp = await self.process_request("flush", req)
        self.assertIsInstance(resp.flush, ResponseFlush)

    async def test_info(self):
        req = Request(info=RequestInfo(version="16"))
        resp = await self.process_request("info", req)
        self.assertIsInstance(resp.info, ResponseInfo)

    async def test_init_chain(self):
        req = Request(init_chain=RequestInitChain())
        resp = await self.process_request("init_chain", req)
        self.assertIsInstance(resp.init_chain, ResponseInitChain)

    async def test_check_tx(self):
        tx_data = b"test_tx_data"
        req = Request(check_tx=RequestCheckTx(tx=tx_data))
        resp = await self.process_request("check_tx", req)
        self.assertIsInstance(resp.check_tx, ResponseCheckTx)

    async def test_query(self):
        req = Request(query=RequestQuery(path="/contract/currency"))
        resp = await self.process_request("query", req)
        self.assertIsInstance(resp.query, ResponseQuery)

    async def test_finalize_block(self):
        req = Request(finalize_block=RequestFinalizeBlock())
        resp = await self.process_request("finalize_block", req)
        self.assertIsInstance(resp.finalize_block, ResponseFinalizeBlock)

    async def test_prepare_proposal(self):
        req = Request(prepare_proposal=RequestPrepareProposal())
        resp = await self.process_request("prepare_proposal", req)
        self.assertIsInstance(resp.prepare_proposal, ResponsePrepareProposal)

    async def test_process_proposal(self):
        req = Request(process_proposal=RequestProcessProposal())
        resp = await self.process_request("process_proposal", req)
        self.assertIsInstance(resp.process_proposal, ResponseProcessProposal)

    async def test_commit(self):
        req = Request(commit=RequestCommit())
        resp = await self.process_request("commit", req)
        self.assertIsInstance(resp.commit, ResponseCommit)

    async def test_no_match(self):
        raw = await self.handler.process("whatever", None)
        resp = await deserialize(raw)
        self.assertEqual(resp.exception.error, "ABCI request not found")

if __name__ == "__main__":
    unittest.main()
