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


def create_state():
    return """
    CREATE TABLE IF NOT EXISTS state (
        key TEXT PRIMARY KEY,
        value JSONB,
        value_numeric NUMERIC GENERATED ALWAYS AS (
            CASE 
                WHEN value::text ~ '^"*[0-9]+(\.[0-9]+)?"*$' 
                THEN (trim(both '"' from value::text))::NUMERIC
                ELSE NULL
            END
        ) STORED,
        updated TIMESTAMP NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_state_value_numeric ON state(value_numeric);
    """


def create_state_changes():
    return """
    CREATE TABLE IF NOT EXISTS state_changes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tx_hash TEXT REFERENCES transactions(hash),
        key TEXT NOT NULL,
        value JSONB,
        value_numeric NUMERIC GENERATED ALWAYS AS (
            CASE 
                WHEN value::text ~ '^"*[0-9]+(\.[0-9]+)?"*$' 
                THEN (trim(both '"' from value::text))::NUMERIC
                ELSE NULL
            END
        ) STORED,
        created TIMESTAMP NOT NULL
    )
    """

    
def create_events():
    return """
-- Create the events table if it doesn't exist
    CREATE TABLE IF NOT EXISTS events (
        id SERIAL PRIMARY KEY, -- Unique identifier for each event
        contract VARCHAR(255) NOT NULL, -- Contract name
        event VARCHAR(255) NOT NULL, -- Event name
        signer VARCHAR(255) NOT NULL, -- Signer of the event
        caller VARCHAR(255) NOT NULL, -- Caller of the event
        data_indexed JSONB NOT NULL, -- Indexed data stored as JSON
        data JSONB NOT NULL, -- Non-indexed data stored as JSON
        tx_hash TEXT REFERENCES transactions(hash),
        created TIMESTAMP NOT NULL
    );

    -- Add a GIN index on the data_indexed column
    CREATE INDEX IF NOT EXISTS idx_data_indexed ON events USING GIN (data_indexed);

    -- Add indexes on contract, signer, and caller columns
    CREATE INDEX IF NOT EXISTS idx_contract ON events (contract);
    CREATE INDEX IF NOT EXISTS idx_signer ON events (signer);
    CREATE INDEX IF NOT EXISTS idx_caller ON events (caller);

    -- Create or replace the function to filter events by data_indexed
    CREATE OR REPLACE FUNCTION public.filter_events_by_data_indexed(key TEXT, value TEXT)
    RETURNS SETOF events AS $$
    BEGIN
    RETURN QUERY
    SELECT * FROM events
    WHERE data_indexed ->> key = value;
    END;
    $$ LANGUAGE plpgsql STABLE;
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


def create_readonly_role():
    return """
    DO $$
    BEGIN
        -- Create the read-only role
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'readonly_user') THEN
            CREATE ROLE readonly_user WITH LOGIN PASSWORD 'readonly';
        END IF;

        -- Grant read-only permissions
        GRANT CONNECT ON DATABASE xian TO readonly_user;
        GRANT USAGE ON SCHEMA public TO readonly_user;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

        -- Ensure future tables also get SELECT permission
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

        -- Set resource limits
        ALTER ROLE readonly_user SET statement_timeout = '1s';
        ALTER ROLE readonly_user SET max_parallel_workers_per_gather = 2;
    END
    $$;
    """


def enforce_table_limits():
    return """
    DO $$
    DECLARE
        rec RECORD;
        schema_name TEXT := 'public'; -- Change this to your schema name
        limit_value INT := 100; -- Change this to your desired limit
    BEGIN
        FOR rec IN
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = schema_name
        LOOP
            EXECUTE format('SELECT * FROM %I.%I LIMIT %s', schema_name, rec.table_name, limit_value);
        END LOOP;
    END $$;
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


def insert_events():
    return """
    INSERT INTO events(
        contract, event, signer, caller, data_indexed, data, tx_hash, created)
    VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8)
    ON CONFLICT (id) DO NOTHING;
    """


def insert_or_update_state():
    return """
    INSERT INTO state(
        key, value, updated)
    VALUES (
        $1, $2, $3)
    ON CONFLICT (key) DO UPDATE SET
        value = EXCLUDED.value,
        updated = EXCLUDED.updated;
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


def select_contracts():
    return """
    SELECT
        *
    FROM 
        contracts
    ORDER BY 
        created ASC
    LIMIT $1 OFFSET $2
    """


def select_state():
    return """
    WITH ranked_state_changes AS (
        SELECT
            key,
            value,
            ROW_NUMBER() OVER (PARTITION BY key ORDER BY created DESC) AS rn
        FROM
            state_changes
        WHERE
            key LIKE $1 || '%'
    )
    SELECT
        key,
        value
    FROM
        ranked_state_changes
    WHERE
        rn = 1
    LIMIT $2 OFFSET $3;
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


def select_state_tx():
    return """
    SELECT
        key, value
    FROM
        state_changes
    WHERE
        tx_hash = $1;
    """


def select_state_block_height():
    return """
    SELECT
        sc.key, sc.value
    FROM
        state_changes sc
    JOIN
        transactions t ON sc.tx_hash = t.hash
    WHERE
        t.block_height = $1;
    """


def select_state_block_hash():
    return """
    SELECT
        sc.key, sc.value
    FROM
        state_changes sc
    JOIN
        transactions t ON sc.tx_hash = t.hash
    WHERE
        t.block_hash = $1;
    """
