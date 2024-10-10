import json

from loguru import logger
from datetime import datetime
from xian.services.bds import sql
from xian.services.bds.config import Config
from contracting.stdlib.bridge.time import Datetime, Timedelta
from xian.services.bds.database import DB, result_to_json
from xian_py.wallet import key_is_valid
from timeit import default_timer as timer


# Custom JSON encoder for our own objects
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Datetime):
            # Convert to ISO 8601 format string with microseconds
            return obj._datetime.isoformat(timespec='microseconds')
        if isinstance(obj, Timedelta):
            # Convert to total seconds
            return obj._timedelta.total_seconds()
        return super().default(obj)

    def encode(self, obj):
        def process(o):
            if isinstance(o, dict):
                return {k: process(v) for k, v in o.items()}
            elif isinstance(o, list):
                return [process(v) for v in o]
            elif isinstance(o, Datetime):
                return o._datetime.isoformat(timespec='microseconds')
            elif isinstance(o, Timedelta):
                return o._timedelta.total_seconds()
            elif isinstance(o, float):
                # Raise an error to prevent precision loss
                raise TypeError("Float values are not allowed due to precision loss. Use integers or strings.")
            else:
                return o
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

        # Insert genesis transaction
        await self.insert_genesis_txn(genesis_state)

        # Process each item in the genesis block
        for index, state in enumerate(genesis_state):
            logger.debug(f"Processing item {index} from genesis_state")
            parts = state["key"].split(".")

            if parts[1] == "__code__":
                submission_time = self.get_submission_time(genesis_state, parts[0])
                await self.insert_genesis_state_contract(parts[0], state["value"], submission_time)
            else:
                await self.insert_genesis_state_change(state["key"], state["value"])
                await self.insert_genesis_state(state["key"], state["value"])

        logger.debug(f'Processed genesis block in {timer() - start_time:.3f} seconds')

    async def __init_tables(self):
        try:
            await self.db.execute(sql.create_transactions())
            await self.db.execute(sql.create_state_changes())
            await self.db.execute(sql.create_rewards())
            await self.db.execute(sql.create_contracts())
            await self.db.execute(sql.create_addresses())
            await self.db.execute(sql.create_readonly_role())
            await self.db.execute(sql.create_state())
            await self.db.execute(sql.enforce_table_limits())
        except Exception as e:
            logger.exception(e)

    async def insert_full_data(self, tx: dict, block_time: datetime):
        total_time = timer()

        # Insert transaction
        start_time = timer()
        await self._insert_tx(tx, block_time)
        logger.debug(f'Saved transaction in {timer() - start_time:.3f} seconds')

        # Insert state
        start_time = timer()
        await self._insert_state(tx, block_time)
        logger.debug(f'Saved state in {timer() - start_time:.3f} seconds')

        # Insert state changes
        start_time = timer()
        await self._insert_state_changes(tx, block_time)
        logger.debug(f'Saved state changes in {timer() - start_time:.3f} seconds')

        # Insert rewards
        start_time = timer()
        await self._insert_rewards(tx, block_time)
        logger.debug(f'Saved rewards in {timer() - start_time:.3f} seconds')

        # Insert addresses
        start_time = timer()
        await self._insert_addresses(tx, block_time)
        logger.debug(f'Saved addresses in {timer() - start_time:.3f} seconds')

        # Insert contracts
        if tx["tx_result"]["status"] == 0:
            start_time = timer()
            await self._insert_contracts(tx, block_time)
            logger.debug(f'Saved contracts in {timer() - start_time:.3f} seconds')

        logger.debug(f'Processed transaction {tx["tx_result"]["hash"]} in {timer() - total_time:.3f} seconds')

    async def _insert_tx(self, tx: dict, block_time: datetime):
        status = tx['tx_result']['status'] == 0
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
        async def insert(reward_type, key, value):
            self.db.add_query_to_batch(sql.insert_rewards(), [
                None,
                tx['tx_result']['hash'],
                reward_type,
                key,
                json.dumps(value, cls=CustomEncoder),
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
                if key_is_valid(address):
                    try:
                        self.db.add_query_to_batch(sql.insert_addresses(), [
                            tx['tx_result']['hash'],
                            address,
                            block_time
                        ])
                    except Exception as e:
                        logger.exception(e)

    async def _insert_contracts(self, tx: dict, block_time: datetime):
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

            results = [dict(row) for row in result]

            # Convert the list of dictionaries to JSON
            results_json = json.dumps(results, default=str)

            return results_json
        except Exception as e:
            logger.exception(e)

    async def get_state(self, key: str, limit: int = 100, offset: int = 0):
        try:
            result = await self.db.fetch(sql.select_state(), [key, limit, offset])

            results = [dict(row) for row in result]

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
        if '@export\ndeftransfer(amount:int,to:str):' not in code:
            return False
        if '@export\ndefapprove(amount:int,to:str):' not in code:
            return False
        if '@export\ndeftransfer_from(amount:int,to:str,main_account:str):' not in code:
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
        try:
            await self.db.execute(sql.insert_contracts(), [
                "GENESIS",
                contract_name,
                code,
                self.is_XSC0001(code),
                submission_time
            ])
        except Exception as e:
            logger.exception(e)

    async def insert_genesis_state_change(self, key, value):
        try:
            await self.db.execute(sql.insert_state_changes(), [
                None,
                "GENESIS",
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
                    return datetime(1970, 1, 1, 0, 0, 0, 0)
                return datetime(1970, 1, 1, 1, 0, 0, 0)
            if isinstance(item, dict) and item.get('key') == f"{contract_name}.__submitted__":
                return datetime(*item["value"].get("__time__"))
        return datetime.now()
