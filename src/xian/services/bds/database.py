import asyncpg

from loguru import logger
from xian.services.bds.config import Config


class DB:

    def __init__(self, config: Config):
        self.cfg = config
        self.pool = None

    async def init_pool(self):
        self.pool = await asyncpg.create_pool(
            user=self.cfg.get('db_user'),
            password=self.cfg.get('db_pass'),
            database=self.cfg.get('db_name'),
            host=self.cfg.get('db_host'),
            port=self.cfg.get('db_port')
        )

    async def execute(self, query: str, params: list = []):
        """
        This is meant for INSERT, UPDATE and DELETE statements
        that usually don't return data
        """
        async with self.pool.acquire() as connection:
            try:
                result = await connection.execute(query, *params)
                return result
            except Exception as e:
                logger.exception(f'Error while executing SQL: {e}')
                raise e

    async def fetch(self, query: str, params: list = []):
        """
        This is meant for statement like SELECT that return data
        """
        async with self.pool.acquire() as connection:
            try:
                result = await connection.fetch(query, *params)
                return result
            except Exception as e:
                logger.exception(f'Error while executing SQL: {e}')
                raise e
