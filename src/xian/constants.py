from pathlib import Path

TENDERMINT_HOME = Path.home() / Path(".tendermint/")
TENDERMINT_CONFIG = TENDERMINT_HOME / Path("config/config.toml")
TENDERMINT_GENESIS = TENDERMINT_HOME / Path("config/genesis.json")

NONCE_FILENAME = '__n'
PENDING_NONCE_FILENAME = '__pn'
STORAGE_HOME = TENDERMINT_HOME / Path('xian/')
