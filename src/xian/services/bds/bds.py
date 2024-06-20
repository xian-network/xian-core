import json

from loguru import logger
from datetime import datetime
from xian.services.bds import sql
from xian.services.bds.config import Config
from xian.services.bds.database import DB
from contracting.stdlib.bridge.decimal import ContractingDecimal
from xian_py.xian_datetime import Timedelta
from contracting.stdlib.bridge.time import Datetime


# Custom JSON encoder for ContractingDecimal
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

    def __init__(self):
        self.db = DB(Config('src', 'xian', 'services', 'bds', 'config.json'))
        self.__init_db()

    def __init_db(self):
        try:
            self.db.execute(sql.create_transactions())
            self.db.execute(sql.create_state_changes())
            self.db.execute(sql.create_rewards())
            self.db.execute(sql.create_contracts())
            self.db.execute(sql.create_addresses())
        except Exception as e:
            logger.exception(e)

    def insert_tx(self, tx: dict):
        try:
            self.db.execute(sql.insert_transaction(), {
                'hash': tx['tx_result']['hash'],
                'contract': tx['payload']['contract'],
                'function': tx['payload']['function'],
                'sender': tx['payload']['sender'],
                'nonce': tx['payload']['nonce'],
                'stamps': tx['tx_result']['stamps_used'],
                'block_hash': tx['b_meta']['hash'],
                'block_height': tx['b_meta']['height'],
                'block_time': tx['b_meta']['nanos'],
                'status': tx['tx_result']['status'],
                'result': tx['tx_result']['result'],
                'json_content': json.dumps(tx, cls=CustomEncoder),
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            logger.exception(e)

    def insert_state_changes(self, tx: dict):
        for state_change in tx['tx_result']['state'].items():
            try:
                self.db.execute(sql.insert_state_changes(), {
                    'id': None,
                    'tx_hash': tx['tx_result']['hash'],
                    'key': state_change['key'],
                    'value': json.dumps(state_change['value'], cls=CustomEncoder),
                    'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.exception(e)

    def insert_rewards(self, tx: dict):
        def insert(reward_type, key, value):
            self.db.execute(sql.insert_rewards(), {
                'id': None,
                'tx_hash': tx['tx_result']['hash'],
                'reward_type': reward_type,
                'key': key,
                'value': value,
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        # Developer reward
        for address, reward in tx['tx_result']['rewards']['developer_rewards'].items():
            try:
                insert('developer_rewards', address, reward)
            except Exception as e:
                logger.exception(e)

        # Masternode reward
        for address, reward in tx['tx_result']['rewards']['masternode_reward'].items():
            try:
                insert('masternode_reward', address, reward)
            except Exception as e:
                logger.exception(e)

        # Foundation reward
        try:
            reward_value = tx['tx_result']['rewards']['foundation_reward']
            insert('foundation_reward', '', reward_value)
        except Exception as e:
            logger.exception(e)

    def insert_addresses(self, tx: dict):
        # TODO: Loop through state and insert everything that has
        # currency.balances:
        try:
            self.db.execute(sql.insert_addresses(), {
                'tx_hash': tx['tx_hash'],
                'address': tx['address'],
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            logger.exception(e)

    def insert_contracts(self, tx: dict):
        if tx['payload']['contract'] == 'submission' and tx['payload']['function'] == 'submit_contract':
            try:
                self.db.execute(sql.insert_contracts(), {
                    'tx_hash': tx['tx_hash'],
                    'name': tx['payload']['kwargs']['name'],
                    'code': tx['payload']['kwargs']['code'],
                    'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.exception(e)
