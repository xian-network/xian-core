from cometbft.abci.v1beta3.types_pb2 import ResponseInitChain
from xian.utils.block import store_genesis_block

import asyncio


async def init_chain(self, req) -> ResponseInitChain:
    abci_genesis_state = self.genesis["abci_genesis"]
    asyncio.ensure_future(store_genesis_block(self.client, self.nonce_storage, abci_genesis_state))

    return ResponseInitChain()
