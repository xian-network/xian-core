from cometbft.abci.v1beta2.types_pb2 import ResponseProcessProposal
from xian.utils import decode_transaction_bytes, encode_transaction

async def process_proposal(self, req) -> ResponseProcessProposal:
    response = ResponseProcessProposal()
    txs = []
    for tx in req.txs:
        try:
            txs.append(decode_transaction_bytes(tx))
        except Exception as e:
            continue
    if txs != sorted(txs):
        response.status = ResponseProcessProposal.ProposalStatus.REJECT
    response.status = ResponseProcessProposal.ProposalStatus.ACCEPT
    return response
