#!/usr/bin/env python3
import requests
import tarfile
import toml
import json
import os
import re
import hashlib

from time import sleep
from pathlib import Path
from argparse import ArgumentParser, BooleanOptionalAction
from typing import Optional, Dict, Any

from xian.constants import Constants as c
from xian.utils.block import is_compiled_key
from contracting.client import ContractingClient
from contracting.storage.driver import Driver
from contracting.storage.encoder import encode
from xian_py.wallet import Wallet
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder, Base64Encoder


class XianConfig:
    """
    Unified configuration tool for Xian nodes. Can be used to:
    1. Generate genesis files only
    2. Configure a node only
    3. Do both genesis generation and node configuration
    """

    COMET_HOME = Path.home() / '.cometbft'
    CONFIG_PATH = COMET_HOME / 'config' / 'config.toml'
    CONTRACT_DIR = Path.cwd() / 'genesis' / 'contracts'
    UNIX_SOCKET_PATH = 'unix:///tmp/abci.sock'

    def __init__(self):
        self.args = self._parse_args()

    def _parse_args(self):
        parser = ArgumentParser(description='Xian node configuration and genesis generation tool')
        parser.add_argument(
            '--mode',
            choices=['genesis', 'node', 'full'],
            required=True,
            help='Operation mode: genesis (generate genesis only), node (configure node only), full (both)'
        )

        # Genesis generation arguments
        parser.add_argument(
            '--founder-privkey',
            type=str,
            help="Founder's private key for genesis generation"
        )
        parser.add_argument(
            '--network',
            type=str,
            default="devnet",
            help='Network type for genesis (devnet, testnet, etc)'
        )
        parser.add_argument(
            '--genesis-path',
            type=Path,
            default=None,
            help="Path for genesis file operations"
        )
        parser.add_argument(
            '--single-node',
            action=BooleanOptionalAction,
            help='Set all contracts to be owned by founder'
        )

        # Node configuration arguments
        parser.add_argument(
            '--validator-privkey',
            type=str,
            help="Validator's private key"
        )
        parser.add_argument(
            '--seed-node',
            type=str,
            help='Seed node IP (e.g., 91.108.112.184)'
        )
        parser.add_argument(
            '--seed-node-address',
            type=str,
            help='Full seed node address (e.g., node_id@91.108.112.184)'
        )
        parser.add_argument(
            '--moniker',
            type=str,
            help='Node name'
        )
        parser.add_argument(
            '--allow-cors',
            action=BooleanOptionalAction,
            default=True,
            help='Enable CORS'
        )
        parser.add_argument(
            '--snapshot-url',
            type=str,
            help='URL of node snapshot (tar.gz)'
        )
        parser.add_argument(
            '--service-node',
            action=BooleanOptionalAction,
            default=False,
            help='Run as a service node'
        )
        parser.add_argument(
            '--enable-pruning',
            action=BooleanOptionalAction,
            default=False,
            help='Enable block pruning'
        )
        parser.add_argument(
            '--blocks-to-keep',
            type=int,
            default=100000,
            help='Number of blocks to keep when pruning'
        )
        parser.add_argument(
            '--prometheus',
            action=BooleanOptionalAction,
            default=True,
            help='Enable Prometheus metrics'
        )

        # Shared arguments
        parser.add_argument(
            '--chain-id',
            type=str,
            default='xian-network',
            help='Chain ID for the network'
        )

        args = parser.parse_args()

        # Validate required arguments based on mode
        if args.mode in ['genesis', 'full'] and not args.founder_privkey:
            parser.error("--founder-privkey is required for genesis generation")
        if args.mode in ['node', 'full']:
            if not args.validator_privkey:
                parser.error("--validator-privkey is required for node configuration")
            if not args.moniker:
                parser.error("--moniker is required for node configuration")

        return args

    def _build_genesis_block(self) -> Dict[str, Any]:
        """Generate the genesis block with contract setup"""
        try:
            contracting = ContractingClient(driver=Driver())
            contracting.set_submission_contract(commit=False)

            wallet = Wallet(seed=self.args.founder_privkey)
            founder_public_key = wallet.public_key

            # Read and process contracts configuration
            con_cfg_path = self.CONTRACT_DIR / f'contracts_{self.args.network}.json'
            with open(con_cfg_path) as f:
                con_cfg = json.load(f)

            # Process each contract
            for contract in con_cfg['contracts']:
                con_path = self.CONTRACT_DIR / (contract['name'] + con_cfg['extension'])

                with open(con_path) as f:
                    code = f.read()

                submit_name = contract.get('submit_as', contract['name'])

                # Process constructor arguments if present
                if contract['constructor_args']:
                    for k, v in contract['constructor_args'].items():
                        if isinstance(v, str) and '%%' in v:
                            result = re.search('%%(.*)%%', v)
                            if result:
                                contract['constructor_args'][k] = v.replace(
                                    result.group(0), locals()[result.group(1)]
                                )

                # Submit contract
                if contracting.get_contract(submit_name) is None:
                    owner = founder_public_key if self.args.single_node else contract['owner']
                    contracting.submit(
                        code,
                        name=submit_name,
                        owner=owner,
                        constructor_args=contract['constructor_args']
                    )

            # Build genesis block structure
            block_number = "0"
            hlc_timestamp = '0000-00-00T00:00:00.000000000Z_0'
            previous_hash = '0' * 64

            # Calculate block hash
            h = hashlib.sha3_256()
            h.update(f'{hlc_timestamp}{block_number}{previous_hash}'.encode())
            block_hash = h.hexdigest()

            # Collect state changes
            genesis_entries = []
            state_changes = contracting.raw_driver.pending_writes
            for key, value in state_changes.items():
                if value is not None and not is_compiled_key(key):
                    genesis_entries.append({'key': key, 'value': value})

            # Sort entries for consistent hashing
            genesis_entries.sort(key=lambda x: x['key'])

            # Calculate state changes hash
            h = hashlib.sha3_256()
            h.update(encode(genesis_entries).encode().encode())
            state_hash = h.hexdigest()

            # Create final block structure
            genesis_block = {
                'hash': block_hash,
                'number': block_number,
                'genesis': genesis_entries,
                'origin': {
                    'signature': wallet.sign_msg(state_hash),
                    'sender': founder_public_key
                }
            }

            return genesis_block

        except Exception as e:
            raise Exception(f"Genesis generation failed: {str(e)}")

    def _write_genesis(self, genesis_block: Dict[str, Any]):
        """Write genesis block to file"""
        try:
            # Determine output paths
            output_path = self.args.genesis_path or (Path.cwd() / 'genesis')
            output_path.mkdir(parents=True, exist_ok=True)

            # Create complete genesis structure
            genesis = {
                'chain_id': self.args.chain_id,
                'abci_genesis': genesis_block
            }

            # Write to file
            output_file = output_path / 'genesis.json'
            with open(output_file, 'w') as f:
                f.write(encode(genesis))

            print(f"Genesis file written to {output_file}")

            return output_file

        except Exception as e:
            raise Exception(f"Failed to write genesis file: {str(e)}")

    def _configure_node(self, genesis_file: Optional[Path] = None):
        """Configure the CometBFT node"""
        try:
            # Check initialization
            if not self.CONFIG_PATH.exists():
                raise Exception('CometBFT is not initialized. Run `cometbft init` first.')

            # Load existing config
            with open(self.CONFIG_PATH, 'r') as f:
                config = toml.load(f)

            # Update configuration
            config.update({
                'chain_id': self.args.chain_id,
                'consensus': {'create_empty_blocks': False},
                'proxy_app': self.UNIX_SOCKET_PATH,
                'moniker': self.args.moniker,
                'instrumentation': {'prometheus': self.args.prometheus},
                'xian': {
                    'block_service_mode': self.args.service_node,
                    'pruning_enabled': self.args.enable_pruning,
                    'blocks_to_keep': self.args.blocks_to_keep
                }
            })

            if self.args.allow_cors:
                config['rpc']['cors_allowed_origins'] = ['*']

            # Handle seed node configuration
            if self.args.seed_node_address:
                config['p2p']['seeds'] = f'{self.args.seed_node_address}:26656'
            elif self.args.seed_node:
                # Query node info
                for attempt in range(10):
                    try:
                        response = requests.get(
                            f'http://{self.args.seed_node}:26657/status',
                            timeout=3
                        )
                        response.raise_for_status()
                        node_id = response.json()['result']['node_info']['id']
                        config['p2p']['seeds'] = f'{node_id}@{self.args.seed_node}:26656'
                        break
                    except Exception:
                        if attempt == 9:
                            print("Warning: Failed to get seed node information")
                        sleep(1)

            # Handle snapshot if provided
            if self.args.snapshot_url:
                for path in [self.COMET_HOME / 'data', self.COMET_HOME / 'xian']:
                    if path.exists():
                        os.system(f'rm -rf {path}')

                # Download and extract snapshot
                response = requests.get(self.args.snapshot_url)
                tar_path = self.COMET_HOME / 'snapshot.tar.gz'
                with open(tar_path, 'wb') as f:
                    f.write(response.content)

                with tarfile.open(tar_path) as tar:
                    tar.extractall(path=self.COMET_HOME)

                os.remove(tar_path)

            # Generate and write validator keys
            if self.args.validator_privkey:
                signing_key = SigningKey(self.args.validator_privkey, encoder=HexEncoder)
                verify_key = signing_key.verify_key

                keys = {
                    "address": hashlib.sha256(verify_key.encode()).digest()[:20].hex().upper(),
                    "pub_key": {
                        "type": "tendermint/PubKeyEd25519",
                        "value": verify_key.encode(encoder=Base64Encoder).decode('utf-8')
                    },
                    'priv_key': {
                        'type': 'tendermint/PrivKeyEd25519',
                        'value': Base64Encoder.encode(
                            signing_key.encode() + verify_key.encode()
                        ).decode('utf-8')
                    }
                }

                key_path = self.COMET_HOME / 'config' / 'priv_validator_key.json'
                with open(key_path, 'w') as f:
                    json.dump(keys, f, indent=2)

            # Copy genesis file if generated
            if genesis_file:
                os.system(f'cp {genesis_file} {c.COMETBFT_GENESIS}')

            # Write updated config
            with open(self.CONFIG_PATH, 'w') as f:
                f.write(toml.dumps(config))

            print('Node configuration complete')
            print('Ensure ports 26656 (P2P) and 26657 (RPC) are open')

        except Exception as e:
            raise Exception(f"Node configuration failed: {str(e)}")

    def run(self):
        """Execute the requested operations"""
        try:
            genesis_file = None

            # Handle genesis generation
            if self.args.mode in ['genesis', 'full']:
                print("Generating genesis block...")
                genesis_block = self._build_genesis_block()
                genesis_file = self._write_genesis(genesis_block)

            # Handle node configuration
            if self.args.mode in ['node', 'full']:
                print("Configuring node...")
                self._configure_node(genesis_file)

            print("All operations completed successfully")

        except Exception as e:
            print(f"Error: {str(e)}")
            raise


if __name__ == '__main__':
    XianConfig().run()