import os
import importlib
import sys
import gc
import asyncio
import signal

from loguru import logger
from datetime import timedelta, datetime
from abci.server import ABCIServer
from xian.constants import Constants
from xian.services.bds.bds import BDS
from contracting.client import ContractingClient

from xian.methods import (
    init_chain,
    echo,
    info,
    check_tx,
    finalize_block,
    commit,
    process_proposal,
    prepare_proposal,
    query,
)
from xian.validators import ValidatorHandler
from xian.nonce import NonceStorage
from xian.processor import TxProcessor
from xian.rewards import RewardsHandler

from xian.utils.cometbft import (
    load_tendermint_config,
    load_genesis_data,
)

from abci.utils import get_logger

get_logger("requests").setLevel(30)
get_logger("urllib3").setLevel(30)
get_logger("asyncio").setLevel(30)

LOG_RETENTION_DAYS = 3


def load_module(module_path, original_module_path):
    """
    Inplace replace of a module with a new one and taking its name.
    """
    try:
        # Replace all functions in the original module with the new modules functions
        module = importlib.import_module(module_path)
        modified_original_module = importlib.import_module(original_module_path)
        for name in dir(module):
            if name.startswith("__"):
                continue
            setattr(modified_original_module, name, getattr(module, name))
        sys.modules[original_module_path] = modified_original_module
        del sys.modules[module_path]
        gc.collect()
        logger.info(f"Loaded module {module_path}")
    except Exception as e:
        raise Exception(f"Failed to load module {module_path}: {e}")


class Xian:
    def __init__(self, constants=Constants()):
        try:
            self.cometbft_config = load_tendermint_config(constants)
            self.genesis = load_genesis_data(constants)
        except Exception as e:
            logger.error(e)
            raise SystemExit()

        self.client = ContractingClient(storage_home=constants.STORAGE_HOME)
        self.nonce_storage = NonceStorage(self.client)
        self.validator_handler = ValidatorHandler(self)
        self.tx_processor = TxProcessor(client=self.client)
        self.rewards_handler = RewardsHandler(client=self.client)
        self.current_block_meta: dict = None
        self.fingerprint_hashes = []
        self.merkle_root_hash = None
        self.chain_id = self.genesis.get("chain_id", None)

        self.block_service_mode = self.cometbft_config["xian"]["block_service_mode"]

        self.pruning_enabled = self.cometbft_config["xian"]["pruning_enabled"]
        # If pruning is enabled, this is the number of blocks to keep history for
        self.blocks_to_keep = self.cometbft_config["xian"]["blocks_to_keep"]
        self.app_version = 1
        if self.chain_id is None:
            raise ValueError("No value set for 'chain_id' in genesis block")

        if self.genesis.get("abci_genesis", None) is None:
            raise ValueError(
                "No value set for 'abci_genesis' in Tendermint genesis.json"
            )

        self.enable_tx_fee = True
        self.static_rewards = False
        self.static_rewards_amount_foundation = 1
        self.static_rewards_amount_validators = 1
        self.current_block_rewards = {}

    @classmethod
    async def create(cls, constants=Constants()):
        self = cls(constants=constants)
        if self.block_service_mode:
            self.bds = await BDS().init(cometbft_genesis=self.genesis)
        return self

    async def echo(self, req):
        """
        Echo a string to test an ABCI client/server implementation
        """
        res = echo.echo(self, req)
        return res

    async def info(self, req):
        """
        Called every time the application starts
        Return information about the application state.
        """
        res = await info.info(self, req)
        return res

    async def init_chain(self, req):
        """Called once upon genesis."""
        resp = await init_chain.init_chain(self, req)
        return resp

    async def check_tx(self, raw_tx):
        """
        Technically optional - not involved in processing blocks.
        Guardian of the mempool: every node runs CheckTx before letting a transaction into its local mempool.
        The transaction may come from an external user or another node
        """
        res = await check_tx.check_tx(self, raw_tx)
        return res

    async def finalize_block(self, req):
        """
        Contains the fields of the newly decided block.
        This method is equivalent to the call sequence BeginBlock, [DeliverTx], and EndBlock in the previous version of ABCI.
        """
        res = await finalize_block.finalize_block(self, req)
        return res

    async def commit(self):
        """
        Signal the Application to persist the application state. Application is expected to persist its state at the end of this call, before calling ResponseCommit.
        """
        res = await commit.commit(self)
        return res

    async def process_proposal(self, req):
        """
        Contains all information on the proposed block needed to fully execute it.
        """
        res = await process_proposal.process_proposal(self, req)
        return res

    async def prepare_proposal(self, req):
        """
        RequestPrepareProposal contains a preliminary set of transactions txs that CometBFT retrieved from the mempool, called raw proposal. The Application can modify this set and return a modified set of transactions via ResponsePrepareProposal.txs .
        """
        res = await prepare_proposal.prepare_proposal(self, req)
        return res

    async def query(self, req):
        """
        Query the application state
        Request Ex. http://localhost:26657/abci_query?path="path"
        """
        res = await query.query(self, req)
        return res


def cleanup_old_logs(logs_dir: str, days: int = 3):
    """Clean up log files older than specified days on startup"""
    try:
        threshold = datetime.now() - timedelta(days=days)
        for f in os.listdir(logs_dir):
            if not f.endswith('.log'):
                continue

            file_path = os.path.join(logs_dir, f)
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))

            if file_time < threshold:
                try:
                    os.remove(file_path)
                    logger.debug(f"Removed old log file: {f}")
                except OSError as e:
                    logger.error(f"Error removing old log file {f}: {e}")
    except Exception as e:
        logger.error(f"Error during log cleanup: {e}")


def main():
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    start_path = os.path.dirname(os.path.realpath(__file__))
    log_path = os.path.realpath(os.path.join(start_path, '..', '..'))
    logs_dir = os.path.join(log_path, 'logs')

    os.makedirs(logs_dir, exist_ok=True)

    # Clean up old logs on startup
    cleanup_old_logs(logs_dir, days=LOG_RETENTION_DAYS)

    logger.add(
        os.path.join(log_path, 'logs', '{time}.log'),
        retention=timedelta(days=LOG_RETENTION_DAYS),
        rotation=timedelta(hours=1),
        format="{time} {level} {name} {message}",
        level="DEBUG",
        enqueue=True,
        compression="zip"  # Compress old logs
    )

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    app = asyncio.get_event_loop().run_until_complete(Xian.create())
    ABCIServer(app=app).run()


def signal_handler(signum, frame):
    logger.info("Shutting down...")
    logger.remove()
    sys.exit(0)


if __name__ == "__main__":
    main()
