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
        success BOOLEAN,
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
        type TEXT NOT NULL,
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
        XSC0001 BOOLEAN DEFAULT FALSE,
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
        block_height, block_time, success, result, json_content, created)
    VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    ON CONFLICT (hash) DO NOTHING;
    """


def insert_state_changes():
    return """
    INSERT INTO state_changes(
        id, tx_hash, key, value, created)
    VALUES (
        COALESCE($1, gen_random_uuid()), $2, $3, $4, $5)
    ON CONFLICT (id) DO NOTHING;
    """


def insert_rewards():
    return """
    INSERT INTO rewards(
        id, tx_hash, type, key, value, created)
    VALUES (
        COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6)
    ON CONFLICT (id) DO NOTHING;
    """


def insert_addresses():
    return """
    INSERT INTO addresses(
        tx_hash, address, created)
    VALUES (
        $1, $2, $3)
    ON CONFLICT (address) DO NOTHING;
    """


def insert_contracts():
    return """
    INSERT INTO contracts(
        tx_hash, name, code, XSC0001, created)
    VALUES (
        $1, $2, $3, $4, $5)
    ON CONFLICT (name) DO NOTHING;
    """


def select_state_history():
    return """
    SELECT 
        key, 
        value, 
        tx_hash, 
        created
    FROM 
        state_changes
    WHERE 
        key = $1
    ORDER BY 
        created DESC
    LIMIT $2 OFFSET $3
    """
