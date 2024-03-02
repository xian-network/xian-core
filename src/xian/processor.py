from xian.utils import format_dictionary, tx_hash_from_tx
from contracting.execution.executor import Executor
from contracting.db.encoder import convert_dict, safe_repr
from contracting.stdlib.bridge.time import Datetime

import math
import hashlib
from datetime import datetime

class TxProcessor():
    def __init__(self, client, driver, metering=False, testing=False):

        self.client = client
        self.driver = driver
        self.executor = Executor(driver=self.driver, metering=metering)


    def process_tx(self, tx, enabled_fees=False):
        # TODO better error handling of anything in here
        # Get the environment
        # print(tx)
        block_meta = tx["b_meta"]
        nanos = block_meta["nanos"]
        environment = self.get_environment(tx=tx)
        # transaction = tx['tx']
        stamp_cost = self.client.get_var(contract='stamp_cost', variable='S', arguments=['value']) or 1

        try:
            # Execute the transaction
            output = self.execute_tx(
                transaction=tx,
                stamp_cost=stamp_cost,
                environment=environment,
                metering=enabled_fees
            )

            # Process the result of the executor
            tx_result = self.process_tx_output(
                output=output,
                transaction=tx,
                stamp_cost=stamp_cost
            )
            
            return {
                'tx_result': tx_result,
                'stamp_rewards_amount': output['stamps_used'],
                'stamp_rewards_contract': tx_result['transaction']['payload']['contract'],
                
            }
        except Exception as e:
            print(e)
            return {
                'tx_result': None,
                'stamp_rewards_amount': 0,
                'stamp_rewards_contract': None
            }

    def execute_tx(self, transaction, stamp_cost, environment: dict = {}, metering=False):
        # TODO better error handling of anything in here
        print("EXECUTING TX")
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
            print("Error executing transaction, skipping.")
            # self.stop_node()

    def process_tx_output(self, output, transaction, stamp_cost):
        # Clear pending writes, stu said to comment this out
        # self.executor.driver.pending_writes.clear()

        # Log out to the node logs if the tx fails
        print(f"status code = {output['status_code']}")
        if output['status_code'] > 0:
            print(f"Transaction failed with status code {output['status_code']}")
            print(f"Transaction: {transaction}")
            print(f"Output: {output}")

        tx_hash = tx_hash_from_tx(transaction)

        writes = self.determine_writes_from_output(
            status_code=output['status_code'],
            ouput_writes=output['writes'],
            stamps_used=output['stamps_used'],
            stamp_cost=stamp_cost,
            tx_sender=transaction['payload']['sender']
        )

        for write in writes:
            self.driver.set(key=write['key'], value=write['value'])

        tx_output = {
            'hash': tx_hash,
            'transaction': transaction,
            'status': output['status_code'],
            'state': writes,
            'stamps_used': output['stamps_used'],
            'result': safe_repr(output['result'])
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
        except Exception as err:
            print("Unable to sort state writes by 'key'.")
            print(err)

        return writes

    def get_environment(self, tx):
        # print(tx)
        block_meta = tx["b_meta"]
        nanos = block_meta["nanos"]
        signature = tx['metadata']['signature']
        # print(f'signature : {signature}')

        # Nanos is set at the time of block being processed, and is shared between all txns in a block.
        # it's a deterministic value which is the average of times from validators who voted for this block TODO : confirm this w/ CometBFT docs.
        # it's set during the consensus agreement & voting for block between all validators.

        return {
            'block_hash': block_meta["hash"],  # hash nanos - # TODO : review
            'block_num': nanos,  # hlc to nanos # TODO : review
            '__input_hash': self.get_hlc_hash_from_tx(nanos, signature),  # Used for deterministic entropy for random games # TODO - REVIEW
            'now': self.get_now_from_nanos(nanos=nanos),
            'AUXILIARY_SALT': signature
        }


    def get_hlc_hash_from_tx(self, nanos, signature):
        h = hashlib.sha3_256()
        h.update('{}'.format(str(nanos)+signature).encode())
        return h.hexdigest()


    def get_now_from_nanos(self, nanos):
        return Datetime._from_datetime(
            datetime.utcfromtimestamp(math.ceil(nanos / 1e9))
        )
