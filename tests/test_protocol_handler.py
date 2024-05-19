import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from io import BytesIO
import logging
from xian.constants import OkCode, ErrorCode
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

# Disable any kind of logging
logging.disable(logging.CRITICAL)

def __deserialze(raw: bytes) -> Request:
    try:
        resp = next(read_messages(BytesIO(raw), Response))
        return resp
    except Exception as e:
        logging.error("Deserialization error: %s", e)
        raise

def test_handler():
    app = Xian()
    p = ProtocolHandler(app)

    def process_request(request_type, req):
        raw = p.process(request_type, req)
        resp = __deserialze(raw)
        return resp

    # flush
    req = Request(flush=RequestFlush())
    resp = process_request("flush", req)
    assert isinstance(resp.flush, ResponseFlush)

    # echo
    req = Request(echo=RequestEcho())
    resp = process_request("echo", req)
    assert isinstance(resp.echo, ResponseEcho)

    # info
    req = Request(info=RequestInfo(version="16"))
    resp = process_request("info", req)
    assert resp.info.version == "16"
    assert resp.info.app_version == 1
    assert resp.info.last_block_height == 0

    # init_chain
    val_a = ValidatorUpdate(power=10, pub_key=PublicKey(ed25519=b"a_pub_key"))
    val_b = ValidatorUpdate(power=10, pub_key=PublicKey(ed25519=b"b_pub_key"))
    v = [val_a, val_b]
    req = Request(init_chain=RequestInitChain(validators=v))
    resp = process_request("init_chain", req)
    assert resp.init_chain.validators._values == [] # If ResponseInitChain.Validators is empty, the initial validator set will be the RequestInitChain.Validators (empty is right)
    assert resp.init_chain.app_hash == b"" # When starting, there is no app hash
    assert isinstance(resp.init_chain.consensus_params, ConsensusParams)
    assert isinstance(resp.init_chain, ResponseInitChain)

    # check_tx
    req = Request(check_tx=RequestCheckTx(tx=b"7b226d65746164617461223a7b227369676e6174757265223a226662333466663762383465623535386464366438623265343330323662326265646565363935346665353631616436326336636164346164373366323866313466323832643565366561663966663062343165613865643731346662313832626263346463383161636563356566626331363462343064326131393835373039227d2c227061796c6f6164223a7b22636861696e5f6964223a227869616e2d746573746e65742d31222c22636f6e7472616374223a227375626d697373696f6e222c2266756e6374696f6e223a227375626d69745f636f6e7472616374222c226b7761726773223a7b22636f6465223a225c6e23204c53543030315c6e62616c616e636573203d20486173682864656661756c745f76616c75653d30295c6e5c6e23204c53543030325c6e6d65746164617461203d204861736828295c6e5c6e40636f6e7374727563745c6e646566207365656428293a5c6e2020202023204c5354303031202d204d494e5420535550504c5920746f2077616c6c65742074686174207375626d6974732074686520636f6e74726163745c6e2020202062616c616e6365735b6374782e63616c6c65725d203d20315f3030305f3030305c6e5c6e2020202023204c53543030325c6e202020206d657461646174615b27746f6b656e5f6e616d65275d203d205c22526f636b657473776170205465737420546f6b656e5c225c6e202020206d657461646174615b27746f6b656e5f73796d626f6c275d203d205c22525357505c225c6e2020202023206d657461646174615b27746f6b656e5f6c6f676f5f75726c275d203d202768747470733a2f2f736f6d652e746f6b656e2e75726c2f746573742d746f6b656e2e706e67275c6e202020206d657461646174615b276f70657261746f72275d203d206374782e63616c6c65725c6e5c6e23204c53543030325c6e406578706f72745c6e646566206368616e67655f6d65746164617461286b65793a207374722c2076616c75653a20416e79293a5c6e20202020617373657274206374782e63616c6c6572203d3d206d657461646174615b276f70657261746f72275d2c20274f6e6c79206f70657261746f722063616e20736574206d6574616461746121275c6e202020206d657461646174615b6b65795d203d2076616c75655c6e5c6e23204c53543030315c6e406578706f72745c6e646566207472616e7366657228616d6f756e743a20666c6f61742c20746f3a20737472293a5c6e2020202061737365727420616d6f756e74203e20302c202743616e6e6f742073656e64206e656761746976652062616c616e63657321275c6e202020206173736572742062616c616e6365735b6374782e63616c6c65725d203e3d20616d6f756e742c20274e6f7420656e6f75676820636f696e7320746f2073656e6421275c6e5c6e2020202062616c616e6365735b6374782e63616c6c65725d202d3d20616d6f756e745c6e2020202062616c616e6365735b746f5d202b3d20616d6f756e745c6e5c6e23204c53543030315c6e406578706f72745c6e64656620617070726f766528616d6f756e743a20666c6f61742c20746f3a20737472293a5c6e2020202061737365727420616d6f756e74203e20302c202743616e6e6f742073656e64206e656761746976652062616c616e63657321275c6e2020202062616c616e6365735b6374782e63616c6c65722c20746f5d202b3d20616d6f756e745c6e5c6e23204c53543030315c6e406578706f72745c6e646566207472616e736665725f66726f6d28616d6f756e743a20666c6f61742c20746f3a207374722c206d61696e5f6163636f756e743a20737472293a5c6e2020202061737365727420616d6f756e74203e20302c202743616e6e6f742073656e64206e656761746976652062616c616e63657321275c6e202020206173736572742062616c616e6365735b6d61696e5f6163636f756e742c206374782e63616c6c65725d203e3d20616d6f756e742c20274e6f7420656e6f75676820636f696e7320617070726f76656420746f2073656e642120596f752068617665207b7d20616e642061726520747279696e6720746f207370656e64207b7d2720202020202020202e666f726d61742862616c616e6365735b6d61696e5f6163636f756e742c206374782e63616c6c65725d2c20616d6f756e74295c6e202020206173736572742062616c616e6365735b6d61696e5f6163636f756e745d203e3d20616d6f756e742c20274e6f7420656e6f75676820636f696e7320746f2073656e6421275c6e5c6e2020202062616c616e6365735b6d61696e5f6163636f756e742c206374782e63616c6c65725d202d3d20616d6f756e745c6e2020202062616c616e6365735b6d61696e5f6163636f756e745d202d3d20616d6f756e745c6e2020202062616c616e6365735b746f5d202b3d20616d6f756e745c6e222c226e616d65223a22636f6e5f74657374696e675f7375626d697373696f6e5f3836343932393539227d2c226e6f6e6365223a362c2273656e646572223a2265396538616164323963653865393466643737643963353535383265356530633537636638316335353262613631633064346533346230646331316664393331222c227374616d70735f737570706c696564223a35303030307d7d"))
    resp = process_request("check_tx", req)
    assert resp.check_tx.code == ErrorCode # Failed Transaction
    assert resp.check_tx.log == "TransactionException: Transaction sender has too few stamps for this transaction" # The log message is appropriate for a failed transaction

    # query
    req = Request(query=RequestQuery(path="/contract/currency"))
    resp = process_request("query", req)
    assert resp.query.code == OkCode #
    assert resp.query.info == "None" # The currency contract is not deployed at this point
    assert resp.query.value == b'\x00' # The value is therefore the default empty byte string

    # finalize_block
    req = Request(finalize_block=RequestFinalizeBlock())
    resp = process_request("finalize_block", req)
    assert isinstance(resp.finalize_block, ResponseFinalizeBlock)

    # prepare_proposal
    req = Request(prepare_proposal=RequestPrepareProposal())
    resp = process_request("prepare_proposal", req)
    assert isinstance(resp.prepare_proposal, ResponsePrepareProposal)

    # process_proposal
    req = Request(process_proposal=RequestProcessProposal())
    resp = process_request("process_proposal", req)
    assert isinstance(resp.process_proposal, ResponseProcessProposal)

    # Commit
    req = Request(commit=RequestCommit())
    resp = process_request("commit", req)
    assert isinstance(resp.commit, ResponseCommit)

    # No match
    raw = p.process("whatever", None)
    resp = __deserialze(raw)
    assert resp.exception.error == "ABCI request not found"

if __name__ == "__main__":
    test_handler()