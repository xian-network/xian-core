from loguru import logger

from xian.services.bds import sql
from xian.services.bds.config import Config
from xian.services.bds.database import DB


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
