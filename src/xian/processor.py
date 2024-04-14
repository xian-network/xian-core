import math
import hashlib
import decimal
from datetime import datetime
from abci.utils import get_logger
from xian.utils import format_dictionary, tx_hash_from_tx
from contracting.execution.executor import Executor
from contracting.db.encoder import convert_dict, safe_repr
from contracting.stdlib.bridge.time import Datetime
from xian.query_eth import ETHQuery

# Logging
logger = get_logger(__name__)


class TxProcessor:
    def __init__(self, client, driver, metering=False):
        self.client = client
        self.driver = driver
        self.executor = Executor(driver=self.driver, metering=metering)
        self.btc_usd_query = ETHQuery(contract_address="0x1b44F3514812d835EB1BDB0acB33d3fA3351Ee43", abi_path="eth_abi/btcusd.json")

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
                stamp_cost=stamp_cost
            )

            return {
                'tx_result': tx_result,
                'stamp_rewards_amount': output['stamps_used'],
                'stamp_rewards_contract': tx_result['transaction']['payload']['contract']
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
            # self.stop_node()

    def process_tx_output(self, output, transaction, stamp_cost):
        # Clear pending writes, stu said to comment this out
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
        except Exception as e:
            logger.error(f"Unable to sort state writes by 'key': {e}")

        return writes

    def get_environment(self, tx):
        # print(tx)
        block_meta = tx["b_meta"]
        nanos = block_meta["nanos"]
        signature = tx['metadata']['signature']
        btc_usd_latest_round = self.btc_usd_query.call_contract('latestRoundData')
        if btc_usd_latest_round is None:
            btc_usd = None
        btc_usd = btc_usd_latest_round['answer']
        btc_usd = decimal.Decimal(btc_usd) / 1e8


        return {
            # Here we can add any other environment variables we want to pass to the contract
            'btc_usd': btc_usd,
            'block_hash': block_meta["hash"],  # hash nanos
            'block_num': block_meta["height"],  # block number
            '__input_hash': self.get_hlc_hash_from_tx(nanos, signature),
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
