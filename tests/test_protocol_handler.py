import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from io import BytesIO

from abci.application import BaseApplication, OkCode
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
    RequestExtendVote,
    ResponseExtendVote,
    RequestVerifyVoteExtension,
    ResponseVerifyVoteExtension,
)
from cometbft.abci.v1beta1.types_pb2 import (
    ResponseInfo,
    RequestQuery,
    ResponseQuery,
    RequestLoadSnapshotChunk,
    ResponseLoadSnapshotChunk,
    RequestListSnapshots,
    ResponseListSnapshots,
    RequestOfferSnapshot,
    ResponseOfferSnapshot,
    RequestApplySnapshotChunk,
    ResponseApplySnapshotChunk,
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

from cometbft.crypto.v1.keys_pb2 import PublicKey


class ExampleApp(BaseApplication):
    def __init__(self):
        self.validators = []

    def info(self, req):
        v = req.version
        r = ResponseInfo(
            version=v,
            data="hello",
            last_block_height=0,
            last_block_app_hash=b"0x12",
        )
        return r

    def init_chain(self, req):
        self.validators = req.validators
        return ResponseInitChain()

    def check_tx(self, tx):
        return ResponseCheckTx(code=OkCode, data=tx, log="bueno")


    def query(self, req):
        d = req.data
        return ResponseQuery(code=OkCode, value=d)

    def commit(self):
        return ResponseCommit()


def __deserialze(raw: bytes) -> Request:
    resp = next(read_messages(BytesIO(raw), Response))
    return resp


def test_handler():
    app = ExampleApp()
    p = ProtocolHandler(app)

    # Flush
    req = Request(flush=RequestFlush())
    raw = p.process("flush", req)
    resp = __deserialze(raw)
    assert isinstance(resp.flush, ResponseFlush)

    # Echo
    req = Request(echo=RequestEcho())
    raw = p.process("echo", req)
    resp = __deserialze(raw)
    assert isinstance(resp.echo, ResponseEcho)

    # Info
    req = Request(info=RequestInfo(version="16"))
    raw = p.process("info", req)
    resp = __deserialze(raw)
    assert resp.info.version == "16"
    assert resp.info.data == "hello"
    assert resp.info.last_block_height == 0
    assert resp.info.last_block_app_hash == b"0x12"

    # init_chain
    val_a = ValidatorUpdate(power=10, pub_key=PublicKey(ed25519=b"a_pub_key"))
    val_b = ValidatorUpdate(power=10, pub_key=PublicKey(ed25519=b"b_pub_key"))

    v = [val_a, val_b]
    req = Request(init_chain=RequestInitChain(validators=v))
    raw = p.process("init_chain", req)
    resp = __deserialze(raw)
    assert isinstance(resp.init_chain, ResponseInitChain)

    # check_tx
    req = Request(check_tx=RequestCheckTx(tx=b"helloworld"))
    raw = p.process("check_tx", req)
    resp = __deserialze(raw)
    assert resp.check_tx.code == OkCode
    assert resp.check_tx.data == b"helloworld"
    assert resp.check_tx.log == "bueno"

    # query
    req = Request(query=RequestQuery(path="/dave", data=b"0x12"))
    raw = p.process("query", req)
    resp = __deserialze(raw)
    assert resp.query.code == OkCode
    assert resp.query.value == b"0x12"

    # finalize_block
    req = Request(finalize_block=RequestFinalizeBlock(txs=[b"one", b"two"]))
    raw = p.process("finalize_block", req)
    resp = __deserialze(raw)
    assert isinstance(resp.finalize_block, ResponseFinalizeBlock)

    # prepare_proposal
    req = Request(prepare_proposal=RequestPrepareProposal())
    raw = p.process("prepare_proposal", req)
    resp = __deserialze(raw)
    assert isinstance(resp.prepare_proposal, ResponsePrepareProposal)

    # process_proposal
    req = Request(process_proposal=RequestProcessProposal())
    raw = p.process("process_proposal", req)
    resp = __deserialze(raw)
    assert isinstance(resp.process_proposal, ResponseProcessProposal)

    # extend_vote
    req = Request(extend_vote=RequestExtendVote())
    raw = p.process("extend_vote", req)
    resp = __deserialze(raw)
    assert isinstance(resp.extend_vote, ResponseExtendVote)

    # verify_vote_extension
    req = Request(verify_vote_extension=RequestVerifyVoteExtension())
    raw = p.process("verify_vote_extension", req)
    resp = __deserialze(raw)
    assert isinstance(resp.verify_vote_extension, ResponseVerifyVoteExtension)

    # load_snapshot_chunk
    req = Request(load_snapshot_chunk=RequestLoadSnapshotChunk())
    raw = p.process("load_snapshot_chunk", req)
    resp = __deserialze(raw)
    assert isinstance(resp.load_snapshot_chunk, ResponseLoadSnapshotChunk)

    # list_snapshots
    req = Request(list_snapshots=RequestListSnapshots())
    raw = p.process("list_snapshots", req)
    resp = __deserialze(raw)
    assert isinstance(resp.list_snapshots, ResponseListSnapshots)

    # offer_snapshot
    req = Request(offer_snapshot=RequestOfferSnapshot())
    raw = p.process("offer_snapshot", req)
    resp = __deserialze(raw)
    assert isinstance(resp.offer_snapshot, ResponseOfferSnapshot)

    # apply_snapshot_chunk
    req = Request(apply_snapshot_chunk=RequestApplySnapshotChunk())
    raw = p.process("apply_snapshot_chunk", req)
    resp = __deserialze(raw)
    assert isinstance(resp.apply_snapshot_chunk, ResponseApplySnapshotChunk)

    # Commit
    req = Request(commit=RequestCommit())
    raw = p.process("commit", req)
    resp = __deserialze(raw)
    assert isinstance(resp.commit, ResponseCommit)

    # No match
    raw = p.process("whatever", None)
    resp = __deserialze(raw)
    assert resp.exception.error == "ABCI request not found"

if __name__ == "__main__":
    test_handler()