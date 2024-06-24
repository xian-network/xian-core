from cometbft.abci.v1beta2.types_pb2 import ResponseProcessProposal


async def process_proposal(self, req) -> ResponseProcessProposal:
    response = ResponseProcessProposal()
    response.status = ResponseProcessProposal.ProposalStatus.ACCEPT
    return response
