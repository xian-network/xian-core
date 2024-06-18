import math
import hashlib

from loguru import logger
from datetime import datetime
from xian.utils import format_dictionary, tx_hash_from_tx, is_compiled_key
from contracting.execution.executor import Executor
from contracting.storage.encoder import convert_dict, safe_repr
from contracting.stdlib.bridge.time import Datetime


class TxProcessor:
    def __init__(self, client, metering=False):
        self.client = client
        self.executor = Executor(driver=self.client.raw_driver, metering=metering)

    def process_tx(self, tx, enabled_fees=False, rewards_handler=None):
        environment = self.get_environment(tx=tx)

        stamp_cost = self.client.get_var(contract='stamp_cost', variable='S', arguments=['value']) or 1

        try:
            # Execute the transaction
            output = self.execute_tx(
                transaction=tx,
                stamp_cost=stamp_cost,
                environment=environment,
                metering=enabled_fees
            )

            if output is None:
                return {
                    'tx_result': None,
                    'stamp_rewards_amount': 0,
                    'stamp_rewards_contract': None
                }

            # Process the result of the executor
            tx_result = self.process_tx_output(
                output=output,
                transaction=tx,
                stamp_cost=stamp_cost,
                rewards_handler=rewards_handler
            )

            tx_result = self.prune_tx_result(tx_result)

            return {
                'tx_result': tx_result,
                'stamp_rewards_amount': output['stamps_used'],
                'stamp_rewards_contract': tx['payload']['contract']
            }
        except Exception as e:
            logger.error(e)

            return {
                'tx_result': None,
                'stamp_rewards_amount': 0,
                'stamp_rewards_contract': None
            }

    def execute_tx(self, transaction, stamp_cost, environment: dict = {}, metering=False):
        # TODO better error handling of anything in here
        logger.debug("Executing transaction...")

        try:
            # Execute transaction
            return self.executor.execute(
                sender=transaction['payload']['sender'],
                contract_name=transaction['payload']['contract'],
                function_name=transaction['payload']['function'],
                stamps=transaction['payload']['stamps_supplied'],
                stamp_cost=stamp_cost,
                kwargs=convert_dict(transaction['payload']['kwargs']),
                environment=environment,
                auto_commit=False,
                metering=metering
            )
        except (TypeError, ValueError) as err:
            import traceback
            traceback.print_exc()
            logger.error(err)
            logger.debug({
                'transaction': transaction,
                'sender': transaction['payload']['sender'],
                'contract_name': transaction['payload']['contract'],
                'function_name': transaction['payload']['function'],
                'stamps': transaction['payload']['stamps_supplied'],
                'stamp_cost': stamp_cost,
                'kwargs': convert_dict(transaction['payload']['kwargs']),
                'environment': environment,
                'auto_commit': False
            })
            return None

    def process_tx_output(self, output, transaction, stamp_cost, rewards_handler):
        # self.executor.driver.pending_writes.clear()
        # Log out to the node logs if the tx fails
        logger.debug(f"status code = {output['status_code']}")

        if output['status_code'] > 0:
            logger.error(
                f'TX executed unsuccessfully. '
                f'{output["stamps_used"]} stamps used. '
                f'{len(output["writes"])} writes. '
                f'Result = {output["result"]}'
            )

        tx_hash = tx_hash_from_tx(transaction)

        writes = self.determine_writes_from_output(
            status_code=output['status_code'],
            ouput_writes=output['writes'],
            stamps_used=output['stamps_used'],
            stamp_cost=stamp_cost,
            tx_sender=transaction['payload']['sender']
        )

        for write in writes:
            self.client.raw_driver.set(key=write['key'], value=write['value'])

        rewards = None
        if rewards_handler is not None:
            calculated_rewards = rewards_handler.calculate_tx_output_rewards(
                total_stamps_to_split=output['stamps_used'],
                contract=transaction['payload']['contract']
            )
            stamp_rate = self.client.get_var(contract='stamp_cost', variable='S', arguments=['value'])
            rewards = {}
            rewards['masternode_reward'] = {}
            for masternode in self.client.get_var(contract='masternodes', variable='nodes'):
                rewards['masternode_reward'][masternode] = calculated_rewards[0] / stamp_rate
            rewards['foundation_reward'] = calculated_rewards[1] / stamp_rate
            rewards['developer_rewards'] = {}
            for developer, reward in calculated_rewards[2].items():
                rewards['developer_rewards'][developer] = reward / stamp_rate
        

        tx_output = {
            'hash': tx_hash,
            'transaction': transaction,
            'status': output['status_code'],
            'state': writes,
            'stamps_used': output['stamps_used'],
            'result': safe_repr(output['result']),
            'rewards': rewards if rewards else None
        }

        tx_output = format_dictionary(tx_output)

        return tx_output

    def determine_writes_from_output(self, status_code, ouput_writes, stamps_used, stamp_cost, tx_sender):
        # Only apply the writes if the tx passes
        if status_code == 0:
            writes = [{'key': k, 'value': v} for k, v in ouput_writes.items()]
        else:
            sender_balance = self.executor.driver.get_var(
                contract='currency',
                variable='balances',
                arguments=[tx_sender],
                mark=False
            )

            # Calculate only stamp deductions
            to_deduct = stamps_used / stamp_cost
            new_bal = 0
            try:
                new_bal = sender_balance - to_deduct
                assert new_bal > 0
            except TypeError:
                pass
            except AssertionError:
                new_bal = 0

            writes = [{
                'key': 'currency.balances:{}'.format(tx_sender),
                'value': new_bal
            }]

        try:
            writes.sort(key=lambda x: x['key'])
        except Exception as e:
            logger.error(f"Unable to sort state writes by 'key': {e}")

        return writes

    def get_environment(self, tx):
        block_meta = tx["b_meta"]
        nanos = block_meta["nanos"]
        signature = tx['metadata']['signature']

        # Nanos is set at the time of block being processed, and is shared between all txns in a block.
        # TODO : confirm this w/ CometBFT docs.
        # it's a deterministic value which is the average of times from validators who voted for this block
        # it's set during the consensus agreement & voting for block between all validators.

        return {
            # TODO: review
            'block_hash': block_meta["hash"],  # hash nanos
            'block_num': block_meta["height"],  # block number
            # TODO: review
            # Used for deterministic entropy for random games
            '__input_hash': self.get_timestamp_hash_from_tx(nanos, signature),
            'now': self.get_now_from_nanos(nanos=nanos),
            'AUXILIARY_SALT': signature
        }

    def get_timestamp_hash_from_tx(self, nanos, signature):
        h = hashlib.sha3_256()
        h.update('{}'.format(str(nanos)+signature).encode())
        return h.hexdigest()

    def get_now_from_nanos(self, nanos):
        return Datetime._from_datetime(
            datetime.utcfromtimestamp(math.ceil(nanos / 1e9))
        )

    def prune_tx_result(self, tx_result: dict):
        # remove compiled code in the case of a contract submission
        tx_result["state"] = [entry for entry in tx_result["state"] if not is_compiled_key(entry["key"])]
        # remove original sent transaction
        tx_result.pop("transaction")
        return tx_result
