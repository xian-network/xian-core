import json
import toml
from xian.constants import Constants

def load_tendermint_config(config: Constants):
    if not (config.COMETBFT_HOME.exists() and config.COMETBFT_HOME.is_dir()):
        raise FileNotFoundError("You must initialize CometBFT first")
    if not (config.COMETBFT_CONFIG.exists() and config.COMETBFT_CONFIG.is_file()):
        raise FileNotFoundError(f"File not found: {config.COMETBFT_CONFIG}")

    return toml.load(config.COMETBFT_CONFIG)


def load_genesis_data(config: Constants):
    if not (config.COMETBFT_GENESIS.exists() and config.COMETBFT_GENESIS.is_file()):
        raise FileNotFoundError(f"File not found: {config.COMETBFT_GENESIS}")

    with open(config.COMETBFT_GENESIS, "r") as file:
        return json.load(file)