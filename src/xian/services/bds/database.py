import psycopg2

from loguru import logger
from psycopg2 import OperationalError
from xian.services.bds.config import Config


class DB:

    cfg = None

    _db_name = None
    _db_user = None
    _db_pass = None
    _db_host = None
    _db_port = None

    def __init__(self, config: Config):
        self.cfg = config

        self._db_name = self.cfg.get('db_name')
        self._db_user = self.cfg.get('db_user')
        self._db_pass = self.cfg.get('db_pass')
        self._db_host = self.cfg.get('db_host')
        self._db_port = self.cfg.get('db_port')

    def _connect(self):
        try:
            connection = psycopg2.connect(
                database=self._db_name,
                user=self._db_user,
                password=self._db_pass,
                host=self._db_host,
                port=self._db_port)
            connection.autocommit = True

            return connection

        except OperationalError as e:
            logger.exception(f'Error while connecting to DB: {e}')

    def execute(self, query: str, params: dict = None):
        con = cur = None

        try:
            con = self._connect()
            cur = con.cursor()

            cur.execute(query, params)
            return cur.fetchall()

        except Exception as e:
            if 'no results to fetch' not in str(e):
                logger.exception(f'Error while executing SQL: {e}')
                raise e

        finally:
            if cur: cur.close()
            if con: con.close()
