"""
To see the latest count:
curl http://localhost:26657/abci_query

The way the app state is structured, you can also see the current state value
in the tendermint console output (see app_hash).
"""

import asyncio
import json
import struct
import time
import binascii


from lamden.crypto.wallet import Wallet
from tendermint.abci.types_pb2 import (
    ResponseInfo,
    ResponseInitChain,
    ResponseCheckTx,
    ResponseDeliverTx,
    ResponseQuery,
    ResponseCommit,
    RequestBeginBlock,
    ResponseBeginBlock,
    RequestEndBlock,
    ResponseEndBlock,
    ResponseCommit,
)

from abci.server import ABCIServer
from abci.application import BaseApplication, OkCode, ErrorCode

from lamden.crypto.wallet import verify
from lamden.crypto.transaction import check_tx_formatting
from contracting.execution.executor import Executor
from contracting.db.encoder import encode, safe_repr, convert_dict
from contracting.client import ContractingClient
from contracting.db.driver import (
    ContractDriver,
    FSDriver,
    Driver,
    AsyncDriver,
    InMemDriver,
    CacheDriver,
)
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.db.encoder import encode, decode
from lamden.crypto.canonical import format_dictionary
from lamden.nodes.base import Lamden


LATEST_BLOCK_HASH_KEY = "__latest_block.hash"
LATEST_BLOCK_HEIGHT_KEY = "__latest_block.height"

# Tx encoding/decoding


def encode_number(value):
    return struct.pack(">I", value)


def decode_number(raw):
    return str.from_bytes(raw, byteorder="big")


def decode_str(raw):
    return str.from_bytes(raw, byteorder="big")


def decode_json(raw):
    return json.loads(raw.decode("utf-8"))


def decode_transaction_bytes(raw):
    tx_bytes = raw
    # Decode the bytes into a string
    tx_hex = tx_bytes.decode("utf-8")
    # Convert the hexadecimal string back into bytes
    tx_decoded_bytes = bytes.fromhex(tx_hex)
    # Decode the bytes into a string
    tx_str = tx_decoded_bytes.decode("utf-8")
    # Parse the string into a JSON object
    tx_json = json.loads(tx_str)
    return tx_json


def unpack_transaction(tx):
    sender = tx["payload"]["sender"]
    signature = tx["metadata"]["signature"]
    encoded_payload = encode(tx["payload"])
    return sender, signature, encoded_payload


def get_nanotime_from_block_time(timeobj) -> int:
    seconds = timeobj.seconds
    nanos = timeobj.nanos
    return int(str(seconds) + str(nanos))


def convert_binary_to_hex(binary_data):
    try:
        return binascii.hexlify(binary_data).decode()
    except UnicodeDecodeError:
        print("The binary data could not be decoded with UTF-8 encoding.")
        raise UnicodeDecodeError(
            "The binary data could not be decoded with UTF-8 encoding."
        )


def get_latest_block_hash(driver: ContractDriver):
    latest_hash = driver.get(LATEST_BLOCK_HASH_KEY)
    if latest_hash is None:
        return b''
    return latest_hash


def set_latest_block_hash(h, driver: ContractDriver):
    driver.set(LATEST_BLOCK_HASH_KEY, h)


def get_latest_block_height(driver: ContractDriver):
    h = driver.get(LATEST_BLOCK_HEIGHT_KEY, save=False)
    if h is None:
        return 0

    if type(h) == ContractingDecimal:
        h = int(h._d)

    return int(h)


def set_latest_block_height(h, driver: ContractDriver):
    driver.set(LATEST_BLOCK_HEIGHT_KEY, int(h))


class Xian(BaseApplication):
    def __init__(self):
        sk = "de6bc6d5ffa7e6fc0c9d618ccad474752256b9936aebddcd70d84fc793255afe"
        self.wallet = Wallet(seed=sk)
        self.client = ContractingClient()
        self.driver = ContractDriver()
        self.lamden = Lamden(
            self.wallet, client=self.client, driver=self.driver
        )
        self.current_block_meta: dict = None

        # current_block_meta :
        # schema :
        # {
        #    nanos: int
        #    height: int
        #    hash: str
        # }
        # set in begin_block
        # used as environment for each tx in block
        # unset at end_block / commit

        # benchmark metrics
        self.tx_count = 0
        self.start_time = time.time()


    def info(self, req) -> ResponseInfo:
        # sk = bytes.fromhex(os.environ['LAMDEN_SK'])
        # wallet = Wallet(seed=sk)
        """
        Called every time the application starts
        """
        r = ResponseInfo()
        r.version = req.version
        r.last_block_height = get_latest_block_height(self.driver)
        r.last_block_app_hash = get_latest_block_hash(self.driver)
        print(f"INFO CALLED")
        print(f"LAST_BLOCK_HEIGHT = {r.last_block_height}")
        print(f"LAST_BLOCK_HHASH = {r.last_block_app_hash}")
        return r


    def init_chain(self, req) -> ResponseInitChain:
        """Called the first time the application starts; when block_height is 0"""

        self.txCount = 0
        self.last_block_height = 0

        with open("genesis_block.json", "r") as f:
            genesis_block = json.load(f)

        asyncio.ensure_future(self.lamden.store_genesis_block(genesis_block))
        contracts = self.client.get_contracts()
        print(contracts)
        return ResponseInitChain()

    def check_tx(self, raw_tx) -> ResponseCheckTx:
        """
        Validate the Tx before entry into the mempool
        Checks the txs are submitted in order 1,2,3...
        If not an order, a non-zero code is returned and the tx
        will be dropped.
        """
        try:
            tx = decode_transaction_bytes(raw_tx)
            sender, signature, encoded_payload = unpack_transaction(tx)

            if verify(vk=sender, msg=encoded_payload, signature=signature):
                # print("VERIFIED")
                return ResponseCheckTx(code=OkCode)
            else:
                print("SIGNATURE VERIFICATION FAILED")
                return ResponseCheckTx(code=ErrorCode)
        except Exception as e:
            print(e)
            return ResponseCheckTx(code=ErrorCode)

    def deliver_tx(self, tx_raw) -> ResponseDeliverTx:
        """
        We have a valid tx, increment the state.
        """
        try:
            tx = decode_transaction_bytes(tx_raw)
            sender, signature, encoded_payload = unpack_transaction(tx)

            if verify(vk=sender, msg=encoded_payload, signature=signature):
                print("DELIVER TX, VERIFIED")
            else:
                print("DELIVER TX, SIGNATURE VERIFICATION FAILED")
                return ResponseDeliverTx(code=ErrorCode)
            tx["b_meta"] = self.current_block_meta
            result = self.lamden.tx_processor.process_tx(tx)
            # print(f"result: {result}")
            self.tx_count += 1

            time_passed = time.time() - self.start_time
            print(
                f"{self.tx_count} processed in {time_passed} at an average of {self.tx_count / time_passed} TPS"
            )
            return ResponseDeliverTx(code=OkCode)
        except Exception as e:
            print(e)
            print("DELIVER TX ERROR")
            ResponseDeliverTx(code=ErrorCode)

    def begin_block(self, req: RequestBeginBlock) -> ResponseBeginBlock:
        print("BEGIN BLOCK")
        nanos = get_nanotime_from_block_time(req.header.time)
        hash = convert_binary_to_hex(req.hash)
        height = req.header.height

        self.current_block_meta = {
            "nanos": nanos,
            "height": height,
            "hash": hash,
        }

        print(self.current_block_meta)

        # print("BEGIN BLOCK")
        """
        Called during the consensus process.

        You can use this to do ``something`` for each new block.
        The overall flow of the calls are:
        begin_block()
        for each tx:
        deliver_tx(tx)
        end_block()
        commit()
        """
        return ResponseBeginBlock()

    def end_block(self, req: RequestEndBlock) -> ResponseEndBlock:
        print("END BLOCK")
        """
        Called at the end of processing the current block. If this is a stateful application
        you can use the height from the request to record the last_block_height
        """

        return ResponseEndBlock()

    def commit(self) -> ResponseCommit:
        print("COMMIT")
        """
        Called after ``end_block``.  This should return a compact ``fingerprint``
        of the current state of the application. This is usually the root hash
        of a merkletree.  The returned data is used as part of the consensus process.
        """
        """Return the current encode state value to tendermint"""
        hash = struct.pack(">Q", self.current_block_meta["nanos"]) # TODO : review this
        # commit block to filesystem db
        set_latest_block_hash(hash, self.driver)
        set_latest_block_height(self.current_block_meta["height"], self.driver)

        self.driver.soft_apply(str(self.current_block_meta["nanos"]))
        self.driver.hard_apply(str(self.current_block_meta["nanos"]))

        # unset current_block_meta
        self.current_block_meta = None
        print(f"COMMIT HASH {hash}")
        return ResponseCommit(data=hash)

    def query(self, req) -> ResponseQuery:
        """Return the last tx count"""
        v = encode_number(self.txCount)
        return ResponseQuery(
            code=OkCode, value=v, height=self.last_block_height
        )


def main():
    app = ABCIServer(app=Xian())
    app.run()


if __name__ == "__main__":
    main()
