from cometbft.abci.v1beta2.types_pb2 import ResponsePrepareProposal


async def prepare_proposal(self, req) -> ResponsePrepareProposal:
    response = ResponsePrepareProposal(txs=req.txs)
    return response
