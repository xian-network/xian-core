import asyncio
import json
import time
import logging
import os

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from cometbft.abci.v1beta1.types_pb2 import (
    ResponseInfo,
    ResponseQuery,
    ResponseEcho,
)
from cometbft.abci.v1beta3.types_pb2 import (
    ResponseInitChain,
    ResponseFinalizeBlock,
    ExecTxResult,    
    ResponseCommit,
    ResponseCheckTx,
)

from cometbft.abci.v1beta2.types_pb2 import (
    ResponsePrepareProposal,
    ResponseProcessProposal,
)


from xian.validators import ValidatorHandler

from abci.server import ABCIServer
from abci.application import BaseApplication, OkCode, ErrorCode
from xian.driver_api import (
    get_latest_block_hash,
    set_latest_block_hash,
    get_latest_block_height,
    set_latest_block_height,
    get_value_of_key,
    get_keys,
)
from xian.rewards import (
    distribute_rewards,
    distribute_static_rewards,)
from xian.utils import (
    encode_str,
    decode_transaction_bytes,
    unpack_transaction,
    get_nanotime_from_block_time,
    convert_binary_to_hex,
    load_tendermint_config,
    stringify_decimals,
    load_genesis_data,
    hash_from_rewards,
    verify,
    hash_list,
    hash_from_rewards
)

from xian.storage import NonceStorage
from contracting.client import ContractingClient
from contracting.db.driver import (
    ContractDriver,
)
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.compilation import parser
from xian.node_base import Node
# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class Xian(BaseApplication):
    def __init__(self):
        try:
            self.config = load_tendermint_config()
            self.genesis = load_genesis_data()
        except Exception as e:
            logger.error(e)
            raise SystemExit()

        self.client = ContractingClient()
        self.driver = ContractDriver()
        self.nonce_storage = NonceStorage()
        self.xian = Node(self.client, self.driver, self.nonce_storage)
        self.validator_handler = ValidatorHandler(self)
        self.current_block_meta: dict = None
        self.fingerprint_hashes = []
        self.fingerprint_hash = None
        self.chain_id = self.genesis.get("chain_id", None)
        self.block_service_mode = self.config.get("block_service_mode", True)
        self.pruning_enabled = self.config.get("pruning_enabled", False) 
        self.blocks_to_keep = self.config.get("blocks_to_keep", 100000) # If pruning is enabled, this is the number of blocks to keep history for

        if self.chain_id is None:
            raise ValueError("No value set for 'chain_id' in genesis block")
        
        if self.genesis.get("abci_genesis", None) is None:
            raise ValueError("No value set for 'abci_genesis' in Tendermint genesis.json")

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
    
    def echo(self, req) -> ResponseEcho:
        r = ResponseEcho()
        r.version = req.version
        r.last_block_height = get_latest_block_height(self.driver)
        r.last_block_app_hash = get_latest_block_hash(self.driver)
        return r

    def info(self, req) -> ResponseInfo:
        """
        Called every time the application starts
        """
        res = ResponseInfo()
        res.version = req.version
        res.last_block_height = get_latest_block_height(self.driver)
        res.last_block_app_hash = get_latest_block_hash(self.driver)
        return res

    def init_chain(self, req) -> ResponseInitChain:
        """Called the first time the application starts; when block_height is 0"""
        abci_genesis_state = self.genesis["abci_genesis"]
        asyncio.ensure_future(self.xian.store_genesis_block(abci_genesis_state))

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
            self.xian.validate_transaction(tx)
            sender, signature, payload = unpack_transaction(tx)
            if not verify(sender, payload, signature):
                return ResponseCheckTx(code=ErrorCode)
            payload_json = json.loads(payload)
            if payload_json["chain_id"] != self.chain_id:
                return ResponseCheckTx(code=ErrorCode)
            return ResponseCheckTx(code=OkCode)
        except Exception as e:
            logger.error(e)
            return ResponseCheckTx(code=ErrorCode, info=f"ERROR: {e}")

    def finalize_block(self, req) -> ResponseFinalizeBlock:
        """
        Called during the consensus process.

        CometBFT, ABCI 2.0 coalesces the BeginBlock, DeliverTx and EndBlock messages into a single message called FinalizeBlock.
        """
        nanos = get_nanotime_from_block_time(req.time)
        hash = convert_binary_to_hex(req.hash)
        height = req.height
        tx_results = []
        reward_writes = []

        self.current_block_meta = {
            "nanos": nanos,
            "height": height,
            "hash": hash,
        }   

        for tx in req.txs: 
            try:
                tx = decode_transaction_bytes(tx)
                # Attach metadata to the transaction
                tx["b_meta"] = self.current_block_meta
                result = self.xian.tx_processor.process_tx(tx, enabled_fees=self.enable_tx_fee)

                if self.enable_tx_fee:
                    self.current_block_rewards[tx['b_meta']['hash']] = {
                        "amount": result["stamp_rewards_amount"],
                        "contract": result["stamp_rewards_contract"]
                    }

                self.xian.set_nonce(tx)
                tx_hash = result["tx_result"]["hash"]
                self.fingerprint_hashes.append(tx_hash)
                parsed_tx_result = json.dumps(stringify_decimals(result["tx_result"]))
                logger.debug(f"parsed tx result : {parsed_tx_result}")
                tx_results.append(ExecTxResult(code=result["tx_result"]["status"],data=encode_str(parsed_tx_result),gas_used=result["stamp_rewards_amount"]))
            except Exception as e:
                # Normally this cannot happen, but if it does, we need to catch it
                logger.error(f"Fatal ERROR: {e}")
                tx_results.append(ExecTxResult(code=ErrorCode, data=encode_str(f"ERROR: {e}"), gas_used=0))

        if self.static_rewards:
            try:
                reward_writes.append(distribute_static_rewards(
                    driver=self.driver,
                    foundation_reward=self.static_rewards_amount_foundation,
                    master_reward=self.static_rewards_amount_validators,
                ))
            except Exception as e:
                logger.error(f"STATIC REWARD ERROR: {e} for block")

        if self.current_block_rewards:
            for tx_hash, reward in self.current_block_rewards.items():
                try:
                    reward_writes.append(distribute_rewards(
                        stamp_rewards_amount=reward["amount"],
                        stamp_rewards_contract=reward["contract"],
                        driver=self.driver,
                        client=self.client,
                    ))

                except Exception as e:
                    logger.error(f"REWARD ERROR: {e} for tx_hash: {tx_hash}")
           
        reward_hash = hash_from_rewards(reward_writes)
        self.fingerprint_hashes.append(reward_hash)
        self.fingerprint_hash = hash_list(self.fingerprint_hashes)

        return ResponseFinalizeBlock(validator_updates=self.validator_handler.build_validator_updates(), tx_results=tx_results, app_hash=self.fingerprint_hash)

    def commit(self) -> ResponseCommit:
        # commit block to filesystem db
        set_latest_block_hash(self.fingerprint_hash, self.driver)
        set_latest_block_height(self.current_block_meta["height"], self.driver)

        self.driver.hard_apply(str(self.current_block_meta["nanos"]))

        # unset current_block_meta & cleanup
        self.current_block_meta = None
        self.fingerprint_hashes = []
        self.fingerprint_hash = None
        self.current_block_rewards = {}

        retain_height = 0 
        if self.pruning_enabled:
            if self.current_block_meta["height"] > self.blocks_to_keep:
                retain_height = self.current_block_meta["height"] - self.blocks_to_keep

        return ResponseCommit(retain_height=retain_height)
    
    def process_proposal(self, req) -> ResponseProcessProposal:
        response = ResponseProcessProposal()
        response.status = ResponseProcessProposal.ProposalStatus.ACCEPT
        return response
    
    def prepare_proposal(self, req) -> ResponsePrepareProposal:
        response = ResponsePrepareProposal(txs=req.txs)
        return response

    # TODO: Probably best to use FastAPI here and add proper error handling
    def query(self, req) -> ResponseQuery:
        """
        Query the application state
        Request Ex. http://localhost:26657/abci_query?path="path"
        (Yes you need to quote the path)
        """

        result = None
        type_of_data = "None"
        key = ""

        try:
            request_path = req.path
            path_parts = [part for part in request_path.split("/") if part]

            # http://localhost:26657/abci_query?path="/get/currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"
            if path_parts and path_parts[0] == "get":
                result = get_value_of_key(path_parts[1], self.driver)
                key = path_parts[1]

            # http://localhost:26657/abci_query?path="/keys/currency.balances" BLOCK SERVICE MODE ONLY
            if self.block_service_mode:
                if path_parts[0] == "keys":
                    result = get_keys(self.driver, path_parts[1])

            # http://localhost:26657/abci_query?path="/health"
            if path_parts[0] == "health":
                result = "OK"

            # http://localhost:26657/abci_query?path="/get_next_nonce/ddd326fddb5d1677595311f298b744a4e9f415b577ac179a6afbf38483dc0791"
            if path_parts[0] == "get_next_nonce":
                result = self.nonce_storage.get_next_nonce(sender=path_parts[1])

            # http://localhost:26657/abci_query?path="/contract/con_some_contract"
            if path_parts[0] == "contract":
                self.client.raw_driver.clear_pending_state()
                result = self.client.raw_driver.get_contract(path_parts[1])

            # http://localhost:26657/abci_query?path="/contract_methods/con_some_contract"
            if path_parts[0] == "contract_methods":
                self.client.raw_driver.clear_pending_state()
                
                contract_code = self.client.raw_driver.get_contract(path_parts[1])
                if contract_code is not None:
                    funcs = parser.methods_for_contract(contract_code)
                    result = {"methods": funcs}

            # http://localhost:26657/abci_query?path="/contract_vars/con_some_contract"
            if path_parts[0] == "contract_vars":
                self.client.raw_driver.clear_pending_state()

                contract_code = self.client.raw_driver.get_contract(path_parts[1])
                if contract_code is not None:
                    result = parser.variables_for_contract(contract_code)

            # http://localhost:26657/abci_query?path="/ping"
            if path_parts[0] == "ping":
                result = {'status': 'online'}

            if result:
                if isinstance(result, str):
                    v = encode_str(result)
                    type_of_data = "str"
                elif isinstance(result, int):
                    v = encode_str(str(result))
                    type_of_data = "int"
                elif isinstance(result, float) or isinstance(result, ContractingDecimal):
                    v = encode_str(str(result))
                    type_of_data = "decimal"
                elif isinstance(result, dict) or isinstance(result, list):
                    v = encode_str(json.dumps(result))
                    type_of_data = "str"
                else:
                    v = encode_str(str(result))
                    type_of_data = "str"
            else:
                # If no result, return a byte string representing None
                v = b"\x00"
                type_of_data = "None"

        except Exception as e:
            logger.error(f"QUERY ERROR: {e}")
            return ResponseQuery(code=ErrorCode, log=f"QUERY ERROR")

        return ResponseQuery(code=OkCode, value=v, info=type_of_data, key=encode_str(key))


def main():
    app = ABCIServer(app=Xian())
    app.run()


if __name__ == "__main__":
    main()
