from cometbft.abci.v1beta2.types_pb2 import ResponsePrepareProposal
from xian.utils import decode_transaction_bytes, encode_transaction


async def prepare_proposal(self, req) -> ResponsePrepareProposal:
    decoded_txs = []
    for tx in req.txs:
        try:
            decoded_txs.append(decode_transaction_bytes(tx))
        except Exception as e:
            continue
    decoded_txs = sorted(decoded_txs)
    txs = [encode_transaction(tx) for tx in decoded_txs]
    response = ResponsePrepareProposal(txs=txs)
    return response
