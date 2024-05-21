import os
import importlib
import sys
import gc

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from loguru import logger
from datetime import timedelta
from abci.server import ABCIServer

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
    query
)
from xian.upgrader import UpgradeHandler
from xian.validators import ValidatorHandler
from xian.storage import NonceStorage
from xian.services.stamp_estimator import StampEstimator
from xian.processor import TxProcessor

from xian.utils import (
    load_tendermint_config,
    load_genesis_data,
)

from abci.utils import get_logger
get_logger("requests").setLevel(30)
get_logger("urllib3").setLevel(30)
get_logger("asyncio").setLevel(30)


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


class Xian():
    def __init__(self):
        try:
            self.config = load_tendermint_config()
            self.genesis = load_genesis_data()
        except Exception as e:
            logger.error(e)
            raise SystemExit()

        self.client = ContractingClient()
        self.nonce_storage = NonceStorage(self.client)
        self.upgrader = UpgradeHandler(self)
        self.validator_handler = ValidatorHandler(self)
        self.tx_processor = TxProcessor(client=self.client)
        self.current_block_meta: dict = None
        self.fingerprint_hashes = []
        self.fingerprint_hash = None
        self.chain_id = self.genesis.get("chain_id", None)
        self.block_service_mode = self.config.get("block_service_mode", True)
        self.stamp_estimator = StampEstimator() if self.block_service_mode else None
        self.pruning_enabled = self.config.get("pruning_enabled", False)
        # If pruning is enabled, this is the number of blocks to keep history for
        self.blocks_to_keep = self.config.get("blocks_to_keep", 100000)
        self.app_version = 1

        if self.chain_id is None:
            raise ValueError("No value set for 'chain_id' in genesis block")

        if self.genesis.get("abci_genesis", None) is None:
            raise ValueError("No value set for 'abci_genesis' in Tendermint genesis.json")

        self.enable_tx_fee = True
        self.static_rewards = False
        self.static_rewards_amount_foundation = 1
        self.static_rewards_amount_validators = 1
        self.current_block_rewards = {}

    def echo(self, req):
        """
        Echo a string to test an ABCI client/server implementation
        """
        res = echo.echo(self, req)
        return res

    def info(self, req):
        """
        Called every time the application starts
        Return information about the application state.
        """
        res = info.info(self, req)
        return res

    def init_chain(self, req):
        """Called once upon genesis."""
        resp = init_chain.init_chain(self, req)
        return resp

    def check_tx(self, raw_tx):
        """
        Technically optional - not involved in processing blocks.
        Guardian of the mempool: every node runs CheckTx before letting a transaction into its local mempool.
        The transaction may come from an external user or another node
        """
        res = check_tx.check_tx(self, raw_tx)
        return res

    def finalize_block(self, req):
        """
        Contains the fields of the newly decided block.
        This method is equivalent to the call sequence BeginBlock, [DeliverTx], and EndBlock in the previous version of ABCI.
        """
        self.upgrader.check_version(req.height)
        res = finalize_block.finalize_block(self, req)
        return res

    def commit(self):
        """
        Signal the Application to persist the application state. Application is expected to persist its state at the end of this call, before calling ResponseCommit.
        """
        res = commit.commit(self)
        return res

    def process_proposal(self, req):
        """
        Contains all information on the proposed block needed to fully execute it.
        """
        res = process_proposal.process_proposal(self, req)
        return res

    def prepare_proposal(self, req):
        """
        RequestPrepareProposal contains a preliminary set of transactions txs that CometBFT retrieved from the mempool, called raw proposal. The Application can modify this set and return a modified set of transactions via ResponsePrepareProposal.txs .
        """
        res = prepare_proposal.prepare_proposal(self, req)
        return res

    def query(self, req):
        """
        Query the application state
        Request Ex. http://localhost:26657/abci_query?path="path"
        """
        res = query.query(self, req)
        return res


def main():
    logger.remove()

    logger.add(
        sys.stderr,
        level='DEBUG')

    logger.add(
        os.path.join('log', '{time}.log'),
        retention=timedelta(days=3),
        format='{time} {level} {name} {message}',
        level='DEBUG',
        rotation='10 MB')

    app = ABCIServer(app=Xian())
    app.run()


if __name__ == "__main__":
    main()
