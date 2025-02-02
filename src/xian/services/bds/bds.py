import json

from loguru import logger
from datetime import datetime
from xian.services.bds import sql
from xian.services.bds.config import Config
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.stdlib.bridge.time import Datetime, Timedelta
from xian.services.bds.database import DB, result_to_json
from xian_py.decompiler import ContractDecompiler
from xian_py.wallet import Wallet
from timeit import default_timer as timer
from decimal import Decimal


# Custom JSON encoder for our own objects
def strip_trailing_zeros(s: str) -> str:
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s


# Encodes everything to string - except for unknown objects
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ContractingDecimal):
            return strip_trailing_zeros(str(obj))
        elif isinstance(obj, Decimal):
            return strip_trailing_zeros(str(obj))
        elif isinstance(obj, Datetime):
            return obj._datetime.isoformat(timespec='microseconds')
        elif isinstance(obj, Timedelta):
            total_seconds = str(obj._timedelta.total_seconds())
            return strip_trailing_zeros(total_seconds)
        elif isinstance(obj, int):
            return str(obj)
        else:
            return super().default(obj)

    # To recursively process and handle custom types within nested structures
    def encode(self, obj):
        def process(o):
            if isinstance(o, dict):
                if len(o) == 1:
                    if '__fixed__' in o:
                        return strip_trailing_zeros(str(o['__fixed__']))
                    elif '__time__' in o:
                        # Convert __time__ list to ISO 8601 string
                        time_list = o['__time__']
                        # Ensure time_list has exactly 7 elements
                        time_list += [0] * (7 - len(time_list))
                        dt_obj = datetime(*time_list)
                        # Convert to ISO 8601 string with microseconds
                        return dt_obj.isoformat(timespec='microseconds')
                # Process nested dictionaries and convert keys to strings
                return {str(k): process(v) for k, v in o.items()}
            elif isinstance(o, list):
                # Process each item in the list
                return [process(v) for v in o]
            elif isinstance(o, ContractingDecimal):
                return strip_trailing_zeros(str(o))
            elif isinstance(o, Decimal):
                return strip_trailing_zeros(str(o))
            elif isinstance(o, Datetime):
                # Serialize datetime as ISO formatted string
                return o._datetime.isoformat(timespec='microseconds')
            elif isinstance(o, Timedelta):
                # Serialize total seconds as a string
                total_seconds = str(o._timedelta.total_seconds())
                return strip_trailing_zeros(total_seconds)
            elif isinstance(o, int):
                return str(o)
            else:
                # Return the object as-is if it doesn't match any custom types
                return o
        # Encode the processed object
        return super().encode(process(obj))


class BDS:
    db = None

    async def init(self, cometbft_genesis: dict):
        self.db = DB(Config('config.json'))

        await self.db.init_pool()
        await self.__init_tables()

        has_entries = await self.db.has_entries("transactions")
        if not has_entries:
            await self.process_genesis_block(cometbft_genesis)

        logger.info('BDS service initialized')
        return self

    async def process_genesis_block(self, cometbft_genesis: dict):
        start_time = timer()

        genesis_state = cometbft_genesis["abci_genesis"]["genesis"]

        # insert genesis txn
        await self.insert_genesis_txn(genesis_state)

        # process each item in the genesis block
        for index, state in enumerate(genesis_state):         
            logger.debug(f"processing item {index} from genesis_state")
            parts = state["key"].split(".")

            if parts[1] == "__code__":
                submission_time = self.get_submission_time(genesis_state, parts[0])
                await self.insert_genesis_state_contract(parts[0], state["value"], submission_time)
            else:
                await self.insert_genesis_state_change(state["key"], state["value"])
                await self.insert_genesis_state(state["key"], state["value"])

        logger.debug(f'Saved genesis block to BDS in {timer() - start_time:.3f} seconds')

    async def __init_tables(self):
        try:
            await self.db.execute(sql.create_transactions())
            await self.db.execute(sql.create_state_changes())
            await self.db.execute(sql.create_rewards())
            await self.db.execute(sql.create_contracts())
            await self.db.execute(sql.create_addresses())
            await self.db.execute(sql.create_readonly_role())
            await self.db.execute(sql.create_state())
            await self.db.execute(sql.create_events())
            await self.db.execute(sql.enforce_table_limits())
        except Exception as e:
            logger.exception(e)


    async def add_to_batch(self, tx: dict, block_time: datetime):
        await self._insert_tx(tx, block_time)
        await self._insert_state(tx, block_time)
        await self._insert_state_changes(tx, block_time)
        await self._insert_rewards(tx, block_time)
        await self._insert_addresses(tx, block_time)
        await self._insert_contracts(tx, block_time)
        await self._insert_events(tx, block_time)

    async def commit_batch(self):
        if len(self.db.batch) == 0: return

        start_time = timer()
        await self.db.commit_batch_to_disk()
        logger.debug(f'Saved block to BDS in {timer() - start_time:.3f} seconds')

    async def _insert_tx(self, tx: dict, block_time: datetime):
        status = True if tx['tx_result']['status'] == 0 else False
        result = None if tx['tx_result']['result'] == 'None' else tx['tx_result']['result']

        try:
            self.db.add_query_to_batch(sql.insert_transaction(), [
                tx['tx_result']['hash'],
                tx['payload']['contract'],
                tx['payload']['function'],
                tx['payload']['sender'],
                tx['payload']['nonce'],
                tx['tx_result']['stamps_used'],
                tx['b_meta']['hash'],
                tx['b_meta']['height'],
                tx['b_meta']['nanos'],
                status,
                result,
                json.dumps(tx, cls=CustomEncoder),
                block_time
            ])
        except Exception as e:
            logger.exception(e)

    async def _insert_state_changes(self, tx: dict, block_time: datetime):
        for state_change in tx['tx_result']['state']:
            try:
                self.db.add_query_to_batch(sql.insert_state_changes(), [
                    None,
                    tx['tx_result']['hash'],
                    state_change['key'],
                    json.dumps(state_change['value'], cls=CustomEncoder),
                    block_time
                ])

            except Exception as e:
                logger.exception(e)

    async def _insert_state(self, tx: dict, block_time: datetime):
        for state_change in tx['tx_result']['state']:
            try:
                self.db.add_query_to_batch(sql.insert_or_update_state(), [
                    state_change['key'],
                    json.dumps(state_change['value'], cls=CustomEncoder),
                    block_time
                ])

            except Exception as e:
                logger.exception(e)

    async def _insert_rewards(self, tx: dict, block_time: datetime):
        async def insert(type, key, value):
            self.db.add_query_to_batch(sql.insert_rewards(), [
                None,
                tx['tx_result']['hash'],
                type,
                key,
                strip_trailing_zeros(str(value)),
                block_time
            ])

        rewards = tx['tx_result']['rewards']

        if rewards:
            # Developer reward
            for address, reward in rewards['developer_reward'].items():
                try:
                    await insert('developer', address, reward)
                except Exception as e:
                    logger.exception(e)

            # Masternode reward
            for address, reward in rewards['masternode_reward'].items():
                try:
                    await insert('masternode', address, reward)
                except Exception as e:
                    logger.exception(e)

            # Foundation reward
            for address, reward in rewards['foundation_reward'].items():
                try:
                    await insert('foundation', address, reward)
                except Exception as e:
                    logger.exception(e)

    async def _insert_addresses(self, tx: dict, block_time: datetime):
        for state_change in tx['tx_result']['state']:
            if state_change['key'].startswith('currency.balances:'):
                address = state_change['key'].replace('currency.balances:', '')
                if Wallet.is_valid_key(address):
                    try:
                        self.db.add_query_to_batch(sql.insert_addresses(), [
                            tx['tx_result']['hash'],
                            address,
                            block_time
                        ])
                    except Exception as e:
                        logger.exception(e)
                        
    async def _insert_events(self, tx: dict, block_time: datetime):
        for event in tx['tx_result']['events']:
            try:
                self.db.add_query_to_batch(sql.insert_events(), [
                    event['contract'],  # Contract name
                    event['event'],     # Event name
                    event['signer'],    # Signer of the event
                    event['caller'],    # Caller of the event
                    json.dumps(event['data_indexed'], cls=CustomEncoder),  # Serialize indexed data
                    json.dumps(event['data'], cls=CustomEncoder),          # Serialize non-indexed data
                    tx['tx_result']['hash'],                
                    block_time                  # Created timestamp
                ])
            except Exception as e:
                logger.exception(e)

    async def _insert_contracts(self, tx: dict, block_time: datetime):
        # Only save contracts if tx was successful
        if tx["tx_result"]["status"] != 0: return

        if tx['payload']['contract'] == 'submission' and tx['payload']['function'] == 'submit_contract':
            try:
                self.db.add_query_to_batch(sql.insert_contracts(), [
                    tx['tx_result']['hash'],
                    tx['payload']['kwargs']['name'],
                    tx['payload']['kwargs']['code'],
                    self.is_XSC0001(tx['payload']['kwargs']['code']),
                    block_time
                ])
            except Exception as e:
                logger.exception(e)

    async def get_contracts(self, limit: int = 100, offset: int = 0):
        try:
            result = await self.db.fetch(sql.select_contracts(), [limit, offset])

            results = []
            for row in result:
                row_dict = dict(row)
                results.append(row_dict)

            # Convert the list of dictionaries to JSON
            results_json = json.dumps(results, default=str)

            return results_json
        except Exception as e:
            logger.exception(e)

    async def get_state(self, key: str, limit: int = 100, offset: int = 0):
        try:
            result = await self.db.fetch(sql.select_state(), [key, limit, offset])

            results = []
            for row in result:
                row_dict = dict(row)
                results.append(row_dict)

            # Convert the list of dictionaries to JSON
            results_json = json.dumps(results, default=str)

            return results_json
        except Exception as e:
            logger.exception(e)

    async def get_state_history(self, key: str, limit: int = 100, offset: int = 0):
        try:
            result = await self.db.fetch(sql.select_state_history(), [key, limit, offset])

            results = []
            for row in result:
                row_dict = dict(row)
                try:
                    # Parse the value column if it contains JSON
                    row_dict['value'] = json.loads(row_dict['value'])
                except (json.JSONDecodeError, TypeError):
                    pass
                results.append(row_dict)

            # Convert the list of dictionaries to JSON
            results_json = json.dumps(results, default=str)

            return results_json
        except Exception as e:
            logger.exception(e)

    async def get_state_for_tx(self, key: str):
        try:
            result = await self.db.fetch(sql.select_state_tx(), [key])
            return result_to_json(result)
        except Exception as e:
            logger.exception(e)

    async def get_state_for_block(self, key: str):
        try:
            if len(key) == 64:
                result = await self.db.fetch(sql.select_state_block_hash(), [key])
            else:
                result = await self.db.fetch(sql.select_state_block_height(), [int(key)])
            return result_to_json(result)
        except Exception as e:
            logger.exception(e)

    def is_XSC0001(self, code: str):
        code = code.replace(' ', '')

        if 'balances=Hash(' not in code:
            return False
        if '@export\ndeftransfer(amount:float,to:str):' not in code:
            return False
        if '@export\ndefapprove(amount:float,to:str):' not in code:
            return False
        if '@export\ndeftransfer_from(amount:float,to:str,main_account:str):' not in code:
            return False
        return True

    async def insert_genesis_txn(self, genesis_state: dict):
        await self.db.execute(sql.insert_transaction(), [
            "GENESIS",
            "GENESIS_SUBMISSION",
            "process_genesis_block",
            "sys",
            0,
            0,
            "GENESIS",
            0,
            0,
            True,
            "OK",
            json.dumps(genesis_state, cls=CustomEncoder),
            datetime.now()
        ])

    async def insert_genesis_state_contract(self, contract_name, code, submission_time):
        original_code = ContractDecompiler().decompile(code)

        try:
            await self.db.execute(sql.insert_contracts(), [
                f"GENESIS",
                contract_name,
                original_code,
                self.is_XSC0001(original_code),
                submission_time
            ])
        except Exception as e:
            logger.exception(e)      

    async def insert_genesis_state_change(self, key, value):
                try:
                    await self.db.execute(sql.insert_state_changes(), [
                        None,
                        f"GENESIS",
                        key,
                        json.dumps(value, cls=CustomEncoder),
                        datetime.now()
                    ])
                except Exception as e:
                    logger.exception(e)

    async def insert_genesis_state(self, key, value):
                try:
                    await self.db.execute(sql.insert_or_update_state(), [
                        key,
                        json.dumps(value, cls=CustomEncoder),
                        datetime.now()
                    ])
                except Exception as e:
                    logger.exception(e)

    def get_submission_time(self, genesis_state: list, contract_name: str) -> datetime:
        for item in genesis_state:
            if "con_" not in contract_name:
                if contract_name == "submission":
                    return datetime(1970,1,1,0,0,0,0)
                return datetime(1970,1,1,1,0,0,0)
            if isinstance(item, dict) and item.get('key') == f"{contract_name}.__submitted__":
                return datetime(*item["value"].get("__time__"))
        return datetime.now()
