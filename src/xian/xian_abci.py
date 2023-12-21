"""
Simple counting app.  It only accepts values sent to it in correct order.  The
state maintains the current count. For example, if starting at state 0, sending:
-> 0x01 = OK!
-> 0x03 = Will fail! (expects 2)

To run it:
- make a clean new directory for tendermint
- start this server: python counter.py
- start tendermint: tendermint --home "YOUR DIR HERE" node
- The send transactions to the app:


curl http://localhost:26657/broadcast_tx_commit?tx=0x01
curl http://localhost:26657/broadcast_tx_commit?tx=0x02
...

To see the latest count:
curl http://localhost:26657/abci_query

The way the app state is structured, you can also see the current state value
in the tendermint console output (see app_hash).
"""
import asyncio
import json
import os
import struct

from lamden.crypto.wallet import Wallet
from tendermint.abci.types_pb2 import (
    ResponseInfo,
    ResponseInitChain,
    ResponseCheckTx,
    ResponseDeliverTx,
    ResponseQuery,
    ResponseCommit,
)

from abci.server import ABCIServer
from abci.application import BaseApplication, OkCode, ErrorCode

from lamden.crypto.wallet import verify
from lamden.crypto.transaction import check_tx_formatting
from contracting.execution.executor import Executor
from contracting.db.encoder import encode, safe_repr, convert_dict
from contracting.client import ContractingClient
from lamden.nodes.base import Lamden

# Tx encoding/decoding


def encode_number(value):
    return struct.pack(">I", value)


def decode_number(raw):
    return int.from_bytes(raw, byteorder="big")


def decode_json(raw):
    return json.loads(raw.decode('utf-8'))


class Xian(BaseApplication):


    def __init__(self):
        sk = "de6bc6d5ffa7e6fc0c9d618ccad474752256b9936aebddcd70d84fc793255afe"
        self.wallet = Wallet(seed=sk)
        self.executor = Executor()
        self.lamden = Lamden(self.wallet)
        self.client = ContractingClient()


    def info(self, req) -> ResponseInfo:
        # sk = bytes.fromhex(os.environ['LAMDEN_SK'])
        # wallet = Wallet(seed=sk)
        """
        Since this will always respond with height=0, Tendermint
        will resync this app from the begining
        """
        r = ResponseInfo()
        r.version = req.version
        r.last_block_height = 0
        r.last_block_app_hash = b""
        return r


    def init_chain(self, req) -> ResponseInitChain:
        print("INIT")
        """Set initial state on first run"""
        self.txCount = 0
        self.last_block_height = 0

        with open('genesis_block.json', 'r') as f:
            genesis_block = json.load(f)

        # loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.lamden.store_genesis_block(genesis_block))
        contracts = self.client.get_contracts()
        print(contracts)
        return ResponseInitChain()


    def check_tx(self, tx) -> ResponseCheckTx:
        """
        Validate the Tx before entry into the mempool
        Checks the txs are submitted in order 1,2,3...
        If not an order, a non-zero code is returned and the tx
        will be dropped.
        """
        tx_json = decode_json(tx)
        if verify(tx_json):
            return ResponseCheckTx(code=ErrorCode)
        return ResponseCheckTx(code=OkCode)


    def deliver_tx(self, tx) -> ResponseDeliverTx:
        """
        We have a valid tx, increment the state.
        """
        try:
            self.executor.execute(
                    sender=tx['payload']['sender'],
                    contract_name=tx['payload']['contract'],
                    function_name=tx['payload']['function'],
                    stamps=tx['payload']['stamps_supplied'],
                    stamp_cost=1, 
                    kwargs=convert_dict(tx['payload']['kwargs']),
                    # environment=environment,
                    auto_commit=False
                )
            return ResponseDeliverTx(code=OkCode)
        except:
            ResponseDeliverTx(code=ErrorCode)


    def query(self, req) -> ResponseQuery:
        """Return the last tx count"""
        v = encode_number(self.txCount)
        return ResponseQuery(
            code=OkCode, value=v, height=self.last_block_height
        )


    def commit(self) -> ResponseCommit:
        """Return the current encode state value to tendermint"""
        hash = struct.pack(">Q", self.txCount)
        return ResponseCommit(data=hash)


def main():
    app = ABCIServer(app=Xian())
    app.run()


if __name__ == "__main__":
    main()
