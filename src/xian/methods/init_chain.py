from cometbft.abci.v1beta3.types_pb2 import ResponseInitChain
import asyncio

def init_chain(self, req) -> ResponseInitChain:
    abci_genesis_state = self.genesis["abci_genesis"]
    asyncio.ensure_future(self.xian.store_genesis_block(abci_genesis_state))

    return ResponseInitChain()