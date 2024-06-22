import json
import asyncio

from loguru import logger
from datetime import datetime
from xian.services.bds import sql
from xian.services.bds.config import Config
from contracting.stdlib.bridge.decimal import ContractingDecimal
from xian_py.xian_datetime import Timedelta
from contracting.stdlib.bridge.time import Datetime
from xian_py.wallet import key_is_valid
from timeit import default_timer as timer
from xian.services.bds.database import DB


# Custom JSON encoder for our own objects
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ContractingDecimal):
            return str(obj)
        if isinstance(obj, Datetime):
            return str(obj)
        if isinstance(obj, Timedelta):
            return str(obj)
        return super().default(obj)


class BDS:
    db = None

    async def init(self):
        self.db = DB(Config('config.json'))
        await self.db.init_pool()
        await self.__init_tables()
        logger.info('BDS service initialized')

    async def __init_tables(self):
        try:
            await self.db.execute(sql.create_transactions())
            await self.db.execute(sql.create_state_changes())
            await self.db.execute(sql.create_rewards())
            await self.db.execute(sql.create_contracts())
            await self.db.execute(sql.create_addresses())
        except Exception as e:
            logger.exception(e)

    async def insert_full_data(self, tx: dict):
        total_time = timer()

        # Tx
        start_time = timer()
        await self._insert_tx(tx)
        logger.debug(f'Saved tx in {timer() - start_time:.3f} seconds')

        # State changes
        start_time = timer()
        await self._insert_state_changes(tx)
        logger.debug(f'Saved state changes in {timer() - start_time:.3f} seconds')

        # Rewards
        start_time = timer()
        await self._insert_rewards(tx)
        logger.debug(f'Saved rewards in {timer() - start_time:.3f} seconds')

        # Addresses
        start_time = timer()
        await self._insert_addresses(tx)
        logger.debug(f'Saved addresses in {timer() - start_time:.3f} seconds')

        # Contracts
        start_time = timer()
        await self.insert_contracts(tx)
        logger.debug(f'Saved contracts in {timer() - start_time:.3f} seconds')

        logger.debug(f'Processed tx {tx["tx_result"]["hash"]} in {timer() - total_time:.3f} seconds')

    async def _insert_tx(self, tx: dict):
        status = True if tx['tx_result']['status'] == 0 else False
        result = None if tx['tx_result']['result'] == 'None' else tx['tx_result']['result']

        try:
            await self.db.execute(sql.insert_transaction(), {
                'hash': tx['tx_result']['hash'],
                'contract': tx['payload']['contract'],
                'function': tx['payload']['function'],
                'sender': tx['payload']['sender'],
                'nonce': tx['payload']['nonce'],
                'stamps': tx['tx_result']['stamps_used'],
                'block_hash': tx['b_meta']['hash'],
                'block_height': tx['b_meta']['height'],
                'block_time': tx['b_meta']['nanos'],
                'success': status,
                'result': result,
                'json_content': json.dumps(tx, cls=CustomEncoder),
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            logger.exception(e)

    async def _insert_state_changes(self, tx: dict):
        for state_change in tx['tx_result']['state']:
            try:
                await self.db.execute(sql.insert_state_changes(), {
                    'id': None,
                    'tx_hash': tx['tx_result']['hash'],
                    'key': state_change['key'],
                    'value': json.dumps(state_change['value'], cls=CustomEncoder),
                    'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.exception(e)

    async def _insert_rewards(self, tx: dict):
        async def insert(type, key, value):
            await self.db.execute(sql.insert_rewards(), {
                'id': None,
                'tx_hash': tx['tx_result']['hash'],
                'type': type,
                'key': key,
                'value': json.dumps(value, cls=CustomEncoder),
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        # Developer reward
        for address, reward in tx['tx_result']['rewards']['developer_reward'].items():
            try:
                await insert('developer', address, float(reward))
            except Exception as e:
                logger.exception(e)

        # Masternode reward
        for address, reward in tx['tx_result']['rewards']['masternode_reward'].items():
            try:
                await insert('masternode', address, float(reward))
            except Exception as e:
                logger.exception(e)

        # Foundation reward
        for address, reward in tx['tx_result']['rewards']['foundation_reward'].items():
            try:
                await insert('foundation', address, float(reward))
            except Exception as e:
                logger.exception(e)

    async def _insert_addresses(self, tx: dict):
        for state_change in tx['tx_result']['state']:
            if state_change['key'].startswith('currency.balances:'):
                address = state_change['key'].replace('currency.balances:', '')
                if key_is_valid(address):
                    try:
                        await self.db.execute(sql.insert_addresses(), {
                            'tx_hash': tx['tx_result']['hash'],
                            'address': address,
                            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    except Exception as e:
                        logger.exception(e)

    async def insert_contracts(self, tx: dict):
        def is_XSC0001(code: str):
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

        if tx['payload']['contract'] == 'submission' and tx['payload']['function'] == 'submit_contract':
            try:
                await self.db.execute(sql.insert_contracts(), {
                    'tx_hash': tx['tx_result']['hash'],
                    'name': tx['payload']['kwargs']['name'],
                    'code': tx['payload']['kwargs']['code'],
                    'XSC0001': is_XSC0001(tx['payload']['kwargs']['code']),
                    'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.exception(e)