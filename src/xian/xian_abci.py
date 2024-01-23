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
import gc
import logging

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
from contracting.db.encoder import encode
from contracting.client import ContractingClient
from contracting.db.driver import (
    ContractDriver,
)
from contracting.stdlib.bridge.decimal import ContractingDecimal
from lamden.crypto.canonical import hash_list
from lamden.nodes.base import Lamden
import logging

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

LATEST_BLOCK_HASH_KEY = "__latest_block.hash"
LATEST_BLOCK_HEIGHT_KEY = "__latest_block.height"


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
    tx_hex = tx_bytes.decode("utf-8")
    tx_decoded_bytes = bytes.fromhex(tx_hex)
    tx_str = tx_decoded_bytes.decode("utf-8")
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
        logger.error(
            "The binary data could not be decoded with UTF-8 encoding."
        )
        raise UnicodeDecodeError(
            "The binary data could not be decoded with UTF-8 encoding."
        )


def get_latest_block_hash(driver: ContractDriver):
    latest_hash = driver.get(LATEST_BLOCK_HASH_KEY)
    if latest_hash is None:
        return b""
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
        self.client = ContractingClient()
        self.driver = ContractDriver()
        self.lamden = Lamden(client=self.client, driver=self.driver)
        self.current_block_meta: dict = None
        self.fingerprint_hashes = []

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
        """
        Called every time the application starts
        """

        r = ResponseInfo()
        r.version = req.version
        r.last_block_height = get_latest_block_height(self.driver)
        r.last_block_app_hash = get_latest_block_hash(self.driver)
        logger.debug(f"LAST_BLOCK_HEIGHT = {r.last_block_height}")
        logger.debug(f"LAST_BLOCK_HASH = {r.last_block_app_hash}")
        return r

    def init_chain(self, req) -> ResponseInitChain:
        """Called the first time the application starts; when block_height is 0"""

        with open("genesis_block.json", "r") as f:
            genesis_block = json.load(f)

        asyncio.ensure_future(self.lamden.store_genesis_block(genesis_block))
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
            if self.lamden.validate_transaction(tx):
                return ResponseCheckTx(code=OkCode)
            else:
                return ResponseCheckTx(code=ErrorCode)
        except Exception as e:
            print(e)
            return ResponseCheckTx(code=ErrorCode)

    def begin_block(self, req: RequestBeginBlock) -> ResponseBeginBlock:
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

        logger.debug(f"BEGIN BLOCK {req.header.height}")

        nanos = get_nanotime_from_block_time(req.header.time)
        hash = convert_binary_to_hex(req.hash)
        height = req.header.height

        self.current_block_meta = {
            "nanos": nanos,
            "height": height,
            "hash": hash,
        }
        self.fingerprint_hashes.append(hash)
        return ResponseBeginBlock()

    def deliver_tx(self, tx_raw) -> ResponseDeliverTx:
        """
        Process each tx from the block & add to cached state.
        """
        try:
            tx = decode_transaction_bytes(tx_raw)
            sender, signature, encoded_payload = unpack_transaction(tx)

            # Verify the contents of the txn before processing.
            if verify(vk=sender, msg=encoded_payload, signature=signature):
                logger.debug("DELIVER TX, SIGNATURE VERIFICATION PASSED")
            else:
                logger.debug("DELIVER TX, SIGNATURE VERIFICATION FAILED")
                return ResponseDeliverTx(code=ErrorCode)

            # Attach metadata to the transaction
            tx["b_meta"] = self.current_block_meta
            result = self.lamden.tx_processor.process_tx(
                tx
            )  # TODO - review how we can pass the result back to a client caller.

            self.lamden.set_nonce(tx)

            tx_hash = result["tx_result"]["hash"]
            self.fingerprint_hashes.append(tx_hash)

            return ResponseDeliverTx(code=OkCode)
        except Exception as e:
            print("DELIVER TX ERROR")
            ResponseDeliverTx(code=ErrorCode)

    def end_block(self, req: RequestEndBlock) -> ResponseEndBlock:
        logger.debug(f"END BLOCK {req.height}")
        """
        Called at the end of processing the current block. If this is a stateful application
        you can use the height from the request to record the last_block_height
        """

        return ResponseEndBlock()

    def commit(self) -> ResponseCommit:
        """
        Called after ``end_block``.  This should return a compact ``fingerprint``
        of the current state of the application. This is usually the root hash
        of a merkletree.  The returned data is used as part of the consensus process.

        Save all cached state from the block to filesystem DB
        """

        logger.debug("COMMIT")

        # a hash of the previous block's app_hash + each of the tx hashes from this block.
        fingerprint_hash = hash_list(self.fingerprint_hashes)

        # commit block to filesystem db
        set_latest_block_hash(fingerprint_hash, self.driver)
        set_latest_block_height(self.current_block_meta["height"], self.driver)

        self.driver.soft_apply(str(self.current_block_meta["nanos"]))
        self.driver.hard_apply(str(self.current_block_meta["nanos"]))

        # unset current_block_meta & cleanup
        self.current_block_meta = None
        self.fingerprint_hashes = []

        gc.collect()

        return ResponseCommit(data=fingerprint_hash)

    def query(self, req) -> ResponseQuery:
        """Return the last tx count"""
        v = encode_number(self.tx_count)
        return ResponseQuery(
            code=OkCode, value=v, height=get_latest_block_height(self.driver)
        )


def main():
    app = ABCIServer(app=Xian())
    app.run()


if __name__ == "__main__":
    main()
