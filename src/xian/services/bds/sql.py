def create_transactions():
    return """
    CREATE TABLE IF NOT EXISTS transactions (
        hash TEXT NOT NULL PRIMARY KEY,
        contract TEXT NOT NULL,
        function TEXT NOT NULL,
        sender TEXT NOT NULL,
        nonce INTEGER NOT NULL,
        stamps INTEGER NOT NULL,
        block_hash TEXT NOT NULL,
        block_height INTEGER NOT NULL,
        block_time BIGINT NOT NULL,
        status INTEGER NOT NULL,
        result TEXT,
        json_content JSONB NOT NULL,
        created TIMESTAMP NOT NULL
    )
    """


def create_state_changes():
    return """
    CREATE TABLE IF NOT EXISTS state_changes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tx_hash TEXT REFERENCES transactions(hash),
        key TEXT NOT NULL,
        value JSONB NOT NULL,
        created TIMESTAMP NOT NULL
    )
    """


def create_rewards():
    return """
    CREATE TABLE IF NOT EXISTS rewards (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tx_hash TEXT REFERENCES transactions(hash),
        reward_type TEXT NOT NULL,
        key TEXT,
        value DECIMAL NOT NULL,
        created TIMESTAMP NOT NULL
    )
    """


def create_addresses():
    return """
    CREATE TABLE IF NOT EXISTS addresses (
        tx_hash TEXT REFERENCES transactions(hash),
        address TEXT NOT NULL PRIMARY KEY,
        created TIMESTAMP NOT NULL
    )
    """


def create_contracts():
    return """
    CREATE TABLE IF NOT EXISTS contracts (
        tx_hash TEXT REFERENCES transactions(hash),
        name TEXT NOT NULL PRIMARY KEY,
        code TEXT NOT NULL,
        created TIMESTAMP NOT NULL
    )
    """


def select_db_size():
    return """
    SELECT pg_size_pretty(pg_database_size(%(n)s))
    """


def insert_transaction():
    return """
    INSERT INTO transactions(
        hash, contract, function, sender, nonce, stamps, block_hash, 
        block_height, block_time, status, result, json_content, created)
    VALUES (
        %(hash)s, %(contract)s, %(function)s, %(sender)s, %(nonce)s, 
        %(stamps)s, %(block_hash)s, %(block_height)s, %(block_time)s, 
        %(status)s, %(result)s, %(json_content)s, %(created)s)
    ON CONFLICT (hash) DO UPDATE 
    SET 
        contract = %(contract)s,
        function = %(function)s,
        sender = %(sender)s,
        nonce = %(nonce)s,
        stamps = %(stamps)s,
        block_hash = %(block_hash)s,
        block_height = %(block_height)s,
        block_time = %(block_time)s,
        status = %(status)s,
        result = %(result)s,
        json_content = %(json_content)s,
        created = %(created)s;
    """


def insert_state_changes():
    return """
    INSERT INTO state_changes(
        id, tx_hash, key, value, created)
    VALUES (
        COALESCE(%(id)s, gen_random_uuid()), %(tx_hash)s, %(key)s, %(value)s, %(created)s)
    ON CONFLICT (id) DO UPDATE 
    SET 
        tx_hash = %(tx_hash)s,
        key = %(key)s,
        value = %(value)s,
        created = %(created)s;
    """


def insert_rewards():
    return """
    INSERT INTO rewards(
        id, tx_hash, key, value, created)
    VALUES (
        COALESCE(%(id)s, gen_random_uuid()), %(tx_hash)s, %(reward_type)s, %(key)s, %(value)s, %(created)s)
    ON CONFLICT (id) DO UPDATE 
    SET 
        tx_hash = %(tx_hash)s,
        reward_type = %(reward_type)s,
        key = %(key)s,
        value = %(value)s,
        created = %(created)s;
    """


def insert_addresses():
    return """
    INSERT INTO addresses(
        tx_hash, address, created)
    VALUES (
        %(tx_hash)s, %(address)s, %(created)s)
    ON CONFLICT (address) DO NOTHING;
    """


def insert_contracts():
    return """
    INSERT INTO contracts(
        tx_hash, name, code, created)
    VALUES (
        %(tx_hash)s, %(name)s, %(code)s, %(created)s)
    ON CONFLICT (name) DO NOTHING;
    """
