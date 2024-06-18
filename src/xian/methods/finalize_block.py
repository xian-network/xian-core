import json

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
    verify,
    hash_list,
    hash_from_rewards,
    hash_from_validator_updates
)
from loguru import logger


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
        tx = decode_transaction_bytes(tx)
        sender, signature, payload = unpack_transaction(tx)
        if not verify(sender, payload, signature):
            # Not really needed, because check_tx should catch this first, but just in case
            continue # Skip this transaction
        # Attach metadata to the transaction
        tx["b_meta"] = self.current_block_meta
        try:
            result = self.tx_processor.process_tx(
                tx,
                enabled_fees=self.enable_tx_fee,
                rewards_handler=self.rewards_handler
            )
        except Exception as e:
            logger.error(f"Error processing tx: {e}")
            continue # Skip this transaction
        self.nonce_storage.set_nonce_by_tx(tx)
        tx_hash = result["tx_result"]["hash"]
        self.fingerprint_hashes.append(tx_hash)
        parsed_tx_result = json.dumps(stringify_decimals(result["tx_result"]))
        logger.debug(f"Parsed tx result: {parsed_tx_result}")

        tx_results.append(
            ExecTxResult(
                code=result["tx_result"]["status"],
                data=encode_str(parsed_tx_result),
                gas_used=0
            )
        )

        if self.block_service_mode:
            print('tx', tx)
            print('tx_result', result)

            # TODO: Make async
            # TODO: Save data in BDS DB

    if self.static_rewards:
        try:
            reward_writes.append(self.rewards_handler.distribute_static_rewards(
                master_reward=self.static_rewards_amount_validators,
                foundation_reward=self.static_rewards_amount_foundation,
            ))
        except Exception as e:
            logger.error(f"STATIC REWARD ERROR: {e} for block")
        
    reward_hash = hash_from_rewards(reward_writes)
    validator_updates = self.validator_handler.build_validator_updates()
    validator_updates_hash = hash_from_validator_updates(validator_updates)
    self.fingerprint_hashes.append(validator_updates_hash)
    self.fingerprint_hashes.append(reward_hash)
    self.fingerprint_hash = hash_list(self.fingerprint_hashes)

    return ResponseFinalizeBlock(
        validator_updates=validator_updates,
        tx_results=tx_results,
        app_hash=self.fingerprint_hash
    )
