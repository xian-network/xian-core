from pathlib import Path
from xian.constants import Constants

class TestConstants(Constants):
    COMETBFT_HOME = Path.home() / Path('/tmp/cometbft/')
    COMETBFT_CONFIG = COMETBFT_HOME / Path("config/config.toml")
    COMETBFT_GENESIS = COMETBFT_HOME / Path("config/genesis.json")

    # NONCE_FILENAME = '__n'
    # PENDING_NONCE_FILENAME = '__pn'
    STORAGE_HOME = COMETBFT_HOME / Path('xian/')

    # LATEST_BLOCK_HASH_KEY = "__latest_block.hash"
    # LATEST_BLOCK_HEIGHT_KEY = "__latest_block.height"
    # DUST_EXPONENT = 8

    # OkCode = 0
    # ErrorCode = 1