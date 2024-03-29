from cometbft.abci.v1beta3.types_pb2 import (
    ResponseFinalizeBlock,
    ExecTxResult
)
from xian.utils import (
    encode_str,
    decode_transaction_bytes,
    unpack_transaction,
    get_nanotime_from_block_time,
    convert_binary_to_hex,
    stringify_decimals,
    hash_from_rewards,
    verify,
    hash_list,
    hash_from_rewards,
    hash_from_validator_updates
)
from xian.rewards import (
    distribute_rewards,
    distribute_static_rewards
)
from abci.application import ErrorCode
import json
import logging

logger = logging.getLogger(__name__)

def finalize_block(self, req) -> ResponseFinalizeBlock:
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
            sender, signature, payload = unpack_transaction(tx)
            if not verify(sender, payload, signature):
                raise Exception("Invalid Signature") # Not really needed, because check_tx should catch this first, but just in case
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
    validator_updates = self.validator_handler.build_validator_updates()
    validator_updates_hash = hash_from_validator_updates(validator_updates)
    self.fingerprint_hashes.append(validator_updates_hash)
    self.fingerprint_hashes.append(reward_hash)
    self.fingerprint_hash = hash_list(self.fingerprint_hashes)

    return ResponseFinalizeBlock(validator_updates=validator_updates, tx_results=tx_results, app_hash=self.fingerprint_hash)