from pathlib import Path

TENDERMINT_HOME = Path.home() / Path(".tendermint/")
TENDERMINT_CONFIG = TENDERMINT_HOME / Path("config/config.toml")
TENDERMINT_GENESIS = TENDERMINT_HOME / Path("config/genesis.json")
