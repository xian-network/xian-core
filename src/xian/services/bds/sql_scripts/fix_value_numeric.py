#!/usr/bin/env python3
"""
Simple script to fix value_numeric columns for scientific notation support
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from database import DB
from config import Config


async def fix_value_numeric():
    """Fix value_numeric columns to handle scientific notation"""
    
    # Your exact SQL
    sql = """
    -- Fix state_changes
    ALTER TABLE state_changes DROP COLUMN value_numeric;

    ALTER TABLE state_changes ADD COLUMN value_numeric NUMERIC GENERATED ALWAYS AS (
        CASE 
            WHEN value::text ~ '^"*-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?"*$' 
            THEN (trim(both '"' from value::text))::NUMERIC
            ELSE NULL
        END
    ) STORED;

    -- Fix state
    ALTER TABLE state DROP COLUMN value_numeric;

    ALTER TABLE state ADD COLUMN value_numeric NUMERIC GENERATED ALWAYS AS (
        CASE 
            WHEN value::text ~ '^"*-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?"*$' 
            THEN (trim(both '"' from value::text))::NUMERIC
            ELSE NULL
        END
    ) STORED;

    CREATE INDEX IF NOT EXISTS idx_state_value_numeric ON state(value_numeric);
    """
    
    # Connect to database
    db = DB(Config('config.json'))
    await db.init_pool()
    logger.info("Database connection initialized")
    
    try:
        logger.info("Executing SQL to fix value_numeric columns...")
        logger.info("This may take a while as PostgreSQL recalculates all existing values...")
        
        await db.execute(sql)
        
        logger.info("✅ SQL executed successfully!")
        logger.info("value_numeric columns now support scientific notation")
        
    except Exception as e:
        logger.error("❌ Failed to execute SQL")
        logger.exception(e)
        raise e
    finally:
        if db.pool:
            await db.pool.close()
            logger.info("Database connection closed")


async def main():
    logger.info("=" * 50)
    logger.info("FIXING VALUE_NUMERIC COLUMNS")
    logger.info("=" * 50)
    
    try:
        await fix_value_numeric()
        return 0
    except Exception as e:
        logger.error("Script failed!")
        return 1


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 