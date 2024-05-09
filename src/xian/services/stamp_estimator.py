from contracting.execution.executor import Executor
from contracting.storage.encoder import safe_repr
from contracting.stdlib.bridge.time import Datetime
from datetime import datetime
from xian.utils import format_dictionary, stringify_decimals
import secrets


class StampEstimator:
    def __init__(self):
        self.executor = Executor(metering=False, bypass_cache=True)

    def generate_environment(self, input_hash='0' * 64, bhash='0' * 64, num=1):
        now = Datetime._from_datetime(
            datetime.now()
        )
        return {
            'block_hash': self.generate_random_hex_string(),
            'block_num': num,
            '__input_hash': self.generate_random_hex_string(),
            'now': now,
            'AUXILIARY_SALT': self.generate_random_hex_string()
        }

    def generate_random_hex_string(self, length=64):
        # Generate a random number with `length//2` bytes and convert to hex
        return secrets.token_hex(nbytes=length // 2)

    def execute_tx(self, transaction, stamp_cost, environment: dict = {}):

        balance = self.executor.driver.get_var(
            contract='currency',
            variable='balances',
            arguments=[transaction['payload']['sender']],
        )

        if balance is None:
            balance = 0
        else:
            balance = int(balance)

        output = self.executor.execute(
            sender=transaction['payload']['sender'],
            contract_name=transaction['payload']['contract'],
            function_name=transaction['payload']['function'],
            stamps=balance * stamp_cost,
            stamp_cost=stamp_cost,
            kwargs=transaction['payload']['kwargs'],
            environment=environment,
            auto_commit=False,
            metering=True
        )

        self.executor.driver.flush_cache()

        writes = [{'key': k, 'value': v} for k, v in output['writes'].items()]

        tx_output = {
            'transaction': transaction,
            'status': output['status_code'],
            'state': writes,
            'stamps_used': output['stamps_used'],
            'result': safe_repr(output['result'])
        }

        tx_output = stringify_decimals(format_dictionary(tx_output))

        return tx_output

    def execute(self, transaction):
        environment = self.generate_environment()
        stamp_cost = int(self.executor.driver.get_var(contract='stamp_cost', variable='S', arguments=['value']))
        return self.execute_tx(
            transaction=transaction,
            environment=environment,
            stamp_cost=stamp_cost
        )
