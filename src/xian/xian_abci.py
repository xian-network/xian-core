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
import os

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

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
    distribute_rewards,
    distribute_static_rewards,
)
from xian.utils import (
    encode_number,
    encode_int,
    encode_str,
    decode_transaction_bytes,
    unpack_transaction,
    get_nanotime_from_block_time,
    convert_binary_to_hex,
    load_tendermint_config,
    stringify_decimals,
    get_genesis_json
)

from lamden.crypto.wallet import verify
from lamden.storage import NonceStorage
from lamden.rewards import RewardManager
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
        config = load_tendermint_config()
        self.genesis = get_genesis_json() 

        self.client = ContractingClient()
        self.driver = ContractDriver()
        self.reward_manager = RewardManager()
        self.nonce_storage = NonceStorage()
        self.lamden = Lamden(client=self.client, driver=self.driver)
        self.current_block_meta: dict = None
        self.fingerprint_hashes = []
        self.chain_id = config.get("chain_id", None)

        if self.chain_id is None:
            raise ValueError("chain_id is not set in the tendermint config")
        
        if self.genesis.get("chain_id") != self.chain_id:
            raise ValueError("chain_id in config.toml does not match the chain_id in the tendermint genesis.json")

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

        self.enable_tx_fee = True
        self.static_rewards = False
        self.static_rewards_amount_foundation = 1
        self.static_rewards_amount_validators = 1

        self.current_block_rewards = {}


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
        logger.debug(f"CHAIN_ID = {self.chain_id}")
        logger.debug(f"BOOTED")
        return r

    def init_chain(self, req) -> ResponseInitChain:
        """Called the first time the application starts; when block_height is 0"""

        abci_genesis_state = self.genesis["abci_genesis"]
        asyncio.ensure_future(self.lamden.store_genesis_block(abci_genesis_state))

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
                payload = json.loads(payload)
                if payload["chain_id"] != self.chain_id:
                    logger.debug("DELIVER TX, CHAIN ID MISMATCH")
                    return ResponseDeliverTx(code=ErrorCode)
                logger.debug("DELIVER TX, SIGNATURE VERIFICATION PASSED")
            else:
                logger.debug("DELIVER TX, SIGNATURE VERIFICATION FAILED")
                return ResponseDeliverTx(code=ErrorCode)

            # Attach metadata to the transaction
            tx["b_meta"] = self.current_block_meta
            result = self.lamden.tx_processor.process_tx(tx, enabled_fees=self.enable_tx_fee)

            if self.enable_tx_fee:
                self.current_block_rewards[tx['b_meta']['hash']] = {"amount": result["stamp_rewards_amount"], "contract": result["stamp_rewards_contract"]}


            self.lamden.set_nonce(tx)
            tx_hash = result["tx_result"]["hash"]
            self.fingerprint_hashes.append(tx_hash)
            parsed_tx_result = json.dumps(stringify_decimals(result["tx_result"]))
            print(parsed_tx_result)
            return ResponseDeliverTx(
                code=OkCode,
                data=encode_str(parsed_tx_result),
                gas_used=result["stamp_rewards_amount"],
            )
        except Exception as err:
            logger.error(f"DELIVER TX ERROR: {err}")
            ResponseDeliverTx(code=ErrorCode)

    def end_block(self, req: RequestEndBlock) -> ResponseEndBlock:
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

        # a hash of the previous block's app_hash + each of the tx hashes from this block.
        fingerprint_hash = hash_list(self.fingerprint_hashes)

        if self.static_rewards:
            distribute_static_rewards(
                driver=self.driver,
                foundation_reward=self.static_rewards_amount_foundation,
                master_reward=self.static_rewards_amount_validators,
            )

        if self.current_block_rewards:
            for tx_hash, reward in self.current_block_rewards.items():
                distribute_rewards(
                    stamp_rewards_amount=reward["amount"],
                    stamp_rewards_contract=reward["contract"],
                    reward_manager=self.reward_manager,
                    driver=self.driver,
                    client=self.client,
                )

        # commit block to filesystem db
        set_latest_block_hash(fingerprint_hash, self.driver)
        set_latest_block_height(self.current_block_meta["height"], self.driver)

        self.driver.hard_apply(str(self.current_block_meta["nanos"]))

        # unset current_block_meta & cleanup
        self.current_block_meta = None
        self.fingerprint_hashes = []

        self.current_block_rewards = {}

        gc.collect()

        return ResponseCommit(data=fingerprint_hash)

    def query(self, req) -> ResponseQuery:
        """
        Query the application state
        Request Ex. http://89.163.130.217:26657/abci_query?path=%22path%22
        (Yes you need to quote the path)
        """

        result = None

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

            if result:
                if isinstance(result, str):
                    v = encode_str(result)
                elif isinstance(result, int):
                    v = encode_int(result)
                elif isinstance(result, float) or isinstance(result, ContractingDecimal):
                    v = encode_number(result)
                elif isinstance(result, dict) or isinstance(result, list):
                    v = encode_str(json.dumps(result))
                else:
                    v = encode_str(str(result))
            else:
                # If no result, return a byte string representing None
                v = b"\x00"

        except Exception as e:
            logger.error(f"QUERY ERROR: {e}")
            return ResponseQuery(code=ErrorCode, log=f"QUERY ERROR")

        return ResponseQuery(code=OkCode, value=v)


def main():
    app = ABCIServer(app=Xian())
    app.run()


if __name__ == "__main__":
    main()
