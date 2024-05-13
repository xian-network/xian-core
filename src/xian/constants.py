from pathlib import Path

TENDERMINT_HOME = Path.home() / Path(".cometbft/")
TENDERMINT_CONFIG = TENDERMINT_HOME / Path("config/config.toml")
TENDERMINT_GENESIS = TENDERMINT_HOME / Path("config/genesis.json")

NONCE_FILENAME = '__n'
PENDING_NONCE_FILENAME = '__pn'
STORAGE_HOME = TENDERMINT_HOME / Path('xian/')

LATEST_BLOCK_HASH_KEY = "__latest_block.hash"
LATEST_BLOCK_HEIGHT_KEY = "__latest_block.height"
DUST_EXPONENT = 8

OkCode = 0
ErrorCode = 1