import hashlib

from loguru import logger
from datetime import datetime
from xian.utils.tx import tx_hash_from_tx, format_dictionary
from xian.utils.block import is_compiled_key
from contracting.execution.executor import Executor
from contracting.stdlib.bridge.time import Datetime

class TxProcessor:
    def __init__(self, client, metering=False):
        self.client = client
        self.executor = Executor(driver=self.client.raw_driver, metering=metering)

    def safe_repr(self, obj, max_len=1024):
        try:
            r = repr(obj)
            rr = r.split(' at 0x')
            if len(rr) > 1:
                return rr[0] + '>'
            return rr[0][:max_len]
        except Exception:
            return None

    def process_tx(self, tx, enabled_fees=False, rewards_handler=None):
        environment = self.get_environment(tx=tx)

        stamp_cost = self.client.get_var(contract='stamp_cost', variable='S', arguments=['value']) or 1
        stamp_cost = int(stamp_cost)  # Ensure stamp_cost is an integer

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
        logger.debug("Executing transaction...")

        try:
            # Convert kwargs if necessary
            kwargs = self.convert_special_types(transaction['payload']['kwargs'])

            # Execute transaction
            return self.executor.execute(
                sender=transaction['payload']['sender'],
                contract_name=transaction['payload']['contract'],
                function_name=transaction['payload']['function'],
                stamps=transaction['payload']['stamps_supplied'],
                stamp_cost=stamp_cost,
                kwargs=kwargs,
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
                'kwargs': kwargs,
                'environment': environment,
                'auto_commit': False
            })
            return None

    def process_tx_output(self, output, transaction, stamp_cost, rewards_handler):
        logger.debug(f"status code = {output['status_code']}")

        if output['status_code'] > 0:
            logger.error(
                f'TX executed unsuccessfully. '
                f'{output["stamps_used"]} stamps used. '
                f'{len(output["writes"])} writes. '
                f'Result = {output["result"]}'
            )

        tx_hash = tx_hash_from_tx(transaction)

        rewards = None
        if output['status_code'] == 0 and rewards_handler is not None:
            # Calculate rewards in stamps
            calculated_rewards = rewards_handler.calculate_tx_output_rewards(
                total_stamps_to_split=output['stamps_used'],
                contract=transaction['payload']['contract']
            )
            stamp_rate = int(self.client.get_var(contract='stamp_cost', variable='S', arguments=['value']))
            foundation_owner = self.client.get_var(contract='foundation', variable='owner')
            rewards = {
                'masternode_reward': {},
                'foundation_reward': {},
                'developer_reward': {}
            }

            # Distribute rewards to masternodes
            masternode_reward_per_node = calculated_rewards[0]  # Assuming this is in stamps
            masternodes = self.client.get_var(contract='masternodes', variable='nodes') or []
            for masternode in masternodes:
                rewards['masternode_reward'][masternode] = masternode_reward_per_node

            # Foundation reward
            foundation_reward = calculated_rewards[1]  # Assuming this is in stamps
            rewards['foundation_reward'][foundation_owner] = foundation_reward

            # Developer rewards
            for developer, reward in calculated_rewards[2].items():
                if developer == 'sys' or developer is None:
                    developer = foundation_owner
                rewards['developer_reward'][developer] = reward  # Assuming reward is in stamps

            state_change_key = "currency.balances"

            # Convert stamps to minimal units of currency
            for address, reward_stamps in rewards['masternode_reward'].items():
                reward_amount = reward_stamps  # Assuming 1 stamp = 1 minimal unit
                write_key = f"{state_change_key}:{address}"
                write_key_balance = self.client.get_var(
                    contract='currency',
                    variable='balances',
                    arguments=[address]
                ) or 0
                if write_key in output['writes']:
                    output['writes'][write_key] += reward_amount
                else:
                    output['writes'][write_key] = write_key_balance + reward_amount

            for address, reward_stamps in rewards['foundation_reward'].items():
                reward_amount = reward_stamps
                write_key = f"{state_change_key}:{address}"
                write_key_balance = self.client.get_var(
                    contract='currency',
                    variable='balances',
                    arguments=[address]
                ) or 0
                if write_key in output['writes']:
                    output['writes'][write_key] += reward_amount
                else:
                    output['writes'][write_key] = write_key_balance + reward_amount

            for address, reward_stamps in rewards['developer_reward'].items():
                reward_amount = reward_stamps
                write_key = f"{state_change_key}:{address}"
                write_key_balance = self.client.get_var(
                    contract='currency',
                    variable='balances',
                    arguments=[address]
                ) or 0
                if write_key in output['writes']:
                    output['writes'][write_key] += reward_amount
                else:
                    output['writes'][write_key] = write_key_balance + reward_amount

        writes = self.determine_writes_from_output(
            status_code=output['status_code'],
            ouput_writes=output['writes'],
            stamps_used=output['stamps_used'],
            stamp_cost=stamp_cost,
            tx_sender=transaction['payload']['sender'],
            rewards=rewards
        )

        for write in writes:
            self.client.raw_driver.set(key=write['key'], value=write['value'])

        tx_output = {
            'hash': tx_hash,
            'transaction': transaction,
            'status': output['status_code'],
            'state': writes,
            'stamps_used': output['stamps_used'],
            'result': self.safe_repr(output['result']),
            'rewards': rewards if rewards else None
        }

        tx_output = format_dictionary(tx_output)

        return tx_output

    def determine_writes_from_output(self, status_code, ouput_writes, stamps_used, stamp_cost, tx_sender, rewards=None):
        # Only apply the writes if the tx passes
        if status_code == 0:
            writes = [{'key': k, 'value': v} for k, v in ouput_writes.items()]
        else:
            sender_balance = self.executor.driver.get_var(
                contract='currency',
                variable='balances',
                arguments=[tx_sender],
                mark=False
            ) or 0

            # Calculate only stamp deductions
            to_deduct = (stamps_used + stamp_cost - 1) // stamp_cost
            new_bal = max(sender_balance - to_deduct, 0)

            writes = [{
                'key': f'currency.balances:{tx_sender}',
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
        chain_id = block_meta["chain_id"]

        return {
            'block_hash': block_meta["hash"],
            'block_num': block_meta["height"],
            '__input_hash': self.get_timestamp_hash_from_tx(nanos, signature),
            'now': self.get_now_from_nanos(nanos=nanos),
            'AUXILIARY_SALT': signature,
            'chain_id': chain_id,
        }

    def get_timestamp_hash_from_tx(self, nanos, signature):
        h = hashlib.sha3_256()
        h.update(f'{nanos}{signature}'.encode())
        return h.hexdigest()

    def get_now_from_nanos(self, nanos):
        return Datetime._from_datetime(
            datetime.utcfromtimestamp(nanos // 1_000_000_000)
        )

    def prune_tx_result(self, tx_result: dict):
        # remove compiled code in the case of a contract submission
        tx_result["state"] = [entry for entry in tx_result["state"] if not is_compiled_key(entry["key"])]
        # remove original sent transaction
        tx_result.pop("transaction")
        return tx_result

    def convert_special_types(self, obj):
        """
        Recursively converts special types in dictionaries or lists.
        """
        if isinstance(obj, dict):
            return {k: self.convert_special_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_special_types(item) for item in obj]
        elif isinstance(obj, float):
            raise TypeError("Float values are not allowed due to precision loss. Use integers or strings.")
        else:
            return obj
