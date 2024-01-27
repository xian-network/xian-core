"""
To see the latest count:
curl http://localhost:26657/abci_query

The way the app state is structured, you can also see the current state value
in the tendermint console output (see app_hash).
"""

import asyncio
import json
import time
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
from xian.driver_api import (
    get_latest_block_hash,
    set_latest_block_hash,
    get_latest_block_height,
    set_latest_block_height,
    get_value_of_key,
)
from xian.utils import (
    encode_number,
    encode_str,
    decode_transaction_bytes,
    unpack_transaction,
    get_nanotime_from_block_time,
    convert_binary_to_hex,
    load_tendermint_config,
)

from lamden.crypto.wallet import verify
from lamden.storage import NonceStorage
from contracting.db.encoder import encode
from contracting.client import ContractingClient
from contracting.db.driver import (
    ContractDriver,
)
from contracting.stdlib.bridge.decimal import ContractingDecimal
from lamden.crypto.canonical import hash_list
from lamden.nodes.base import Lamden
from pathlib import Path

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class Xian(BaseApplication):
    def __init__(self):
        self.client = ContractingClient()
        self.driver = ContractDriver()
        self.nonce_storage = NonceStorage()
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

        load_tendermint_config()

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

        genesis_file = "genesis_block.json"

        if Path(genesis_file).is_file():
            with open(genesis_file, "r") as f:
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
            sender, signature, payload = unpack_transaction(tx)

            # Verify the contents of the txn before processing.
            if verify(vk=sender, msg=payload, signature=signature):
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
        """
        Query the application state
        Request Ex. http://89.163.130.217:26657/abci_query?path=%22path%22
        (Yes you need to quote the path)
        """
        
        result = ""
        
        try:
            request_path = req.path
            path_parts = [part for part in request_path.split("/") if part]

            # http://89.163.130.217:26657/abci_query?path="/get/currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"
            if path_parts and path_parts[0] == "get":
                result = get_value_of_key(path_parts[1], self.driver)

            # http://89.163.130.217:26657/abci_query?path="/health"
            if path_parts[0] == "health":
                result = "OK"

            # http://89.163.130.217:26657/abci_query?path="/get_next_nonce/ddd326fddb5d1677595311f298b744a4e9f415b577ac179a6afbf38483dc0791"
            if path_parts[0] == "get_next_nonce":
                result = self.nonce_storage.get_next_nonce(sender=path_parts[1])

            if path_parts[0] == "estimate_stamps":
                contract_name = path_parts[1]
                function_name = path_parts[2]
                kwargs = json.loads(path_parts[3])
                result = self.client.estimate_stamps(contract_name=contract_name, function_name=function_name, kwargs=kwargs)

            if isinstance(result, str):
                v = encode_str(result)
            elif isinstance(result, int) or isinstance(result, float) or isinstance(result, ContractingDecimal):
                v = encode_number(result)
            elif isinstance(result, dict) or isinstance(result, list):
                v = encode_str(json.dumps(result))
            else:
                v = encode_str(str(result))

        except Exception as e:
            logger.error(f"QUERY ERROR: {e}")
            return ResponseQuery(code=ErrorCode, log=f"QUERY ERROR")

        return ResponseQuery(code=OkCode, value=v)


def main():
    app = ABCIServer(app=Xian())
    app.run()


if __name__ == "__main__":
    main()
