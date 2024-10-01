import json
import asyncpg

from loguru import logger
from xian.services.bds.config import Config


def result_to_json(result):
    results = []
    for row in result:
        row_dict = dict(row)
        results.append(row_dict)

    # Convert the list of dictionaries to JSON
    return json.dumps(results, default=str)


class DB:

    batch = []

    def __init__(self, config: Config):
        self.cfg = config
        self.pool = None

    async def init_pool(self):
        # Create a temporary connection to the default database to check/create the target database
        temp_conn = await asyncpg.connect(
            user=self.cfg.get('db_user'),
            password=self.cfg.get('db_pass'),
            database='postgres',  # Connect to the default 'postgres' database
            host=self.cfg.get('db_host'),
            port=self.cfg.get('db_port')
        )
        try:
            # Check if the target database exists
            result = await temp_conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                self.cfg.get('db_name')
            )
            if not result:
                # Create the target database if it does not exist
                await temp_conn.execute(
                    f"CREATE DATABASE {self.cfg.get('db_name')}"
                )
        finally:
            await temp_conn.close()

        # Now create the connection pool to the target database
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

    def add_query_to_batch(self, query: str, args: list):
        self.batch.append((query, args))

    async def commit_batch_to_disk(self):
        async with self.pool.acquire() as connection:
            try:
                for query, params in self.batch:
                    await connection.execute(query, *params)
            except Exception as e:
                logger.exception(f'Error while executing SQL: {e}')
                raise e
            finally:
                self.batch = []

    async def fetch(self, query: str, params: list = []):
        """
        This is meant for SELECT statements that return data
        """
        async with self.pool.acquire() as connection:
            try:
                result = await connection.fetch(query, *params)
                return result
            except Exception as e:
                logger.exception(f'Error while executing SQL: {e}')
                raise e

    async def has_entries(self, table_name: str) -> bool:
        try:
            result = await self.fetch(f"SELECT COUNT(*) as count FROM {table_name}")
            logger.debug(result)
            return result[0]['count'] > 0
        except Exception as e:
            logger.exception(e)
            return False
