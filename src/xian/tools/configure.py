import requests
import tarfile
import toml
import json
import os
import hashlib

from time import sleep
from pathlib import Path
from argparse import ArgumentParser

from xian.constants import Constants as c
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder, Base64Encoder
from argparse import BooleanOptionalAction

"""
Configure CometBFT node
"""


# TODO: Set chain_id through this too
class Configure:
    """
    Snapshot should be a tar.gz file containing
    the data directory and xian directory

    File priv_validator_state.json from snapshot should have
    round and step set to 0 and signature, signbytes removed
    """

    COMET_HOME = Path.home() / '.cometbft'
    CONFIG_PATH = COMET_HOME / 'config' / 'config.toml'
    UNIX_SOCKET_PATH = 'unix:///tmp/abci.sock'

    def __init__(self):
        parser = ArgumentParser(description='Configure CometBFT')
        parser.add_argument(
            '--seed-node',
            type=str,
            help='IP of Seed Node e.g. 91.108.112.184 (without port, but 26657 & 26656 need to be open). For joining an existing network, populates node id from querying node.',
            required=False
        )
        parser.add_argument(
            '--seed-node-address',
             type=str,
             help='Seed node address e.g. <node_id>@91.108.112.184 . For cold booting a test network.',
             required=False
        )
        parser.add_argument(
            '--moniker',
            type=str,
            help='Name of your node',
            required=True
        )
        parser.add_argument(
            '--allow-cors',
            action=BooleanOptionalAction,
            help='Allow CORS',
            required=False,
            default=True
        )
        parser.add_argument(
            '--snapshot-url',
            type=str,
            help='URL of snapshot in tar.gz format',
            required=False
        )
        parser.add_argument(
            '--generate-genesis',
            action=BooleanOptionalAction,
            help='Generate genesis file',
            required=False,
            default=False
        )
        parser.add_argument(
            '--copy-genesis',
            action=BooleanOptionalAction,
            help='Copy genesis file',
            required=True
        )
        parser.add_argument(
            '--genesis-file-name',
            type=str,
            help='Genesis filename if copy-genesis is True e.g. genesis-testnet.json',
            required=True,
            default="genesis-testnet.json"
        )
        parser.add_argument(
            '--validator-privkey',
            type=str,
            help="Validator's private key",
            required=True
        )
        parser.add_argument(
            '--founder-privkey',
            type=str,
            help="Founder's private key",
            required=False
        )
        parser.add_argument(
            '--prometheus',
            action=BooleanOptionalAction,
            help='Enable Prometheus',
            required=False,
            default=True
        )
        parser.add_argument(
            '--service-node',
            action=BooleanOptionalAction,
            help='If the node is a service node',
            required=False,
            default=False
        )
        parser.add_argument(
            '--enable-pruning',
            action=BooleanOptionalAction,
            help='Prune blocks. Related to "blocks-to-keep" value',
            required=False,
            default=False
        )
        parser.add_argument(
            '--blocks-to-keep',
            type=int,
            help='Number of blocks to keep. Related to "enable-pruning" value',
            required=False,
            default=100000
        )

        self.args = parser.parse_args()

    def get_node_info(self, seed_node):
        attempts = 0
        max_attempts = 10
        timeout = 3  # seconds
        while attempts < max_attempts:
            try:
                response = requests.get(f'http://{seed_node}:26657/status', timeout=timeout)
                response.raise_for_status()  # Raises stored HTTPError, if one occurred.
                return response.json()
            except requests.exceptions.HTTPError as err:
                print(f"HTTP error: {err}")
            except requests.exceptions.ConnectionError as err:
                print(f"Connection error: {err}")
            except requests.exceptions.Timeout as err:
                print(f"Timeout error: {err}")
            except requests.exceptions.RequestException as err:
                print(f"Error: {err}")

            attempts += 1
            sleep(1)  # wait 1 second before trying again

        return None  # or raise an Exception indicating the request ultimately failed
    
    def download_and_extract(self, url, target_path):
        # Download the file from the URL
        response = requests.get(url)
        # Assumes the URL ends with the filename
        filename = url.split('/')[-1]
        tar_path = target_path / filename
        # Ensure the target directory exists
        os.makedirs(target_path, exist_ok=True)
        
        # Save the downloaded file to disk
        with open(tar_path, 'wb') as file:
            file.write(response.content)
        
        # Extract the tar.gz file
        if tar_path.endswith(".tar.gz"):
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=target_path)
        elif tar_path.endswith(".tar"):
            with tarfile.open(tar_path, "r:") as tar:
                tar.extractall(path=target_path)
        else:
            print("File format not recognized. Please use a .tar.gz or .tar file.")
        
        os.remove(tar_path)

    def generate_keys(self):
        pk_hex = self.args.validator_privkey

        # Convert hex private key to bytes and generate signing key object
        signing_key = SigningKey(pk_hex, encoder=HexEncoder)

        # Obtain the verify key (public key) from the signing key
        verify_key = signing_key.verify_key

        # Concatenate private and public key bytes
        priv_key_with_pub = signing_key.encode() + verify_key.encode()

        # Encode concatenated private and public keys in Base64 for the output
        priv_key_with_pub_b64 = Base64Encoder.encode(priv_key_with_pub).decode('utf-8')

        # Encode public key in Base64 for the output
        public_key_b64 = verify_key.encode(encoder=Base64Encoder).decode('utf-8')

        # Hash the public key using SHA-256 and take the first 20 bytes for the address
        address_bytes = hashlib.sha256(verify_key.encode()).digest()[:20]
        address = address_bytes.hex().upper()

        output = {
            "address": address,
            "pub_key": {
                "type": "tendermint/PubKeyEd25519",
                "value": public_key_b64
            },
            'priv_key': {
                'type': 'tendermint/PrivKeyEd25519',
                'value': priv_key_with_pub_b64
            }
        }
        return output

    def main(self):
        # Make sure this is run in the tools directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        if not os.path.exists(self.CONFIG_PATH):
            print('Initialize CometBFT first')
            return

        with open(self.CONFIG_PATH, 'r') as f:
            config = toml.load(f)

        config['consensus']['create_empty_blocks'] = False

        if self.args.seed_node_address:
            config['p2p']['seeds'] = f'{self.args.seed_node_address}:26656'
        # Otherwise construct the seed node address from the IP
        if self.args.seed_node:
            info = self.get_node_info(self.args.seed_node)

            if info:
                id = info['result']['node_info']['id']
                config['p2p']['seeds'] = f'{id}@{self.args.seed_node}:26656'
            else:
                print("Failed to get node information after 10 attempts.")

        config['xian'] = {
            'block_service_mode': self.args.service_node,
            'pruning_enabled': self.args.enable_pruning,
            'blocks_to_keep': self.args.blocks_to_keep
        }

        config['proxy_app'] = self.UNIX_SOCKET_PATH

        if self.args.moniker:
            config['moniker'] = self.args.moniker

        if self.args.allow_cors:
            config['rpc']['cors_allowed_origins'] = ['*']

        if self.args.snapshot_url:
            # If data directory exists, delete it
            data_dir = self.COMET_HOME / 'data'
            if os.path.exists(data_dir):
                os.system(f'rm -rf {data_dir}')
            # If xian directory exists, delete it
            xian_dir = self.COMET_HOME / 'xian'
            if os.path.exists(xian_dir):
                os.system(f'rm -rf {xian_dir}')

            # Download snapshot
            self.download_and_extract(self.args.snapshot_url, self.COMET_HOME)

        # Generate genesis
        if self.args.generate_genesis:
            if not self.args.validator_privkey:
                print('Validator private key is required')
                return
            if not self.args.founder_privkey:
                print('Founder private key is required')
                return

            # Generate validator_pubkey from validator_privkey
            seed = bytes.fromhex(self.args.validator_privkey)
            sk = SigningKey(seed=seed)
            vk = sk.verify_key

            validator_pubkey = vk.encode().hex()

            os.system(f'python3 genesis_gen.py '
                      f'--validator-pubkey {validator_pubkey} '
                      f'--founder-privkey {self.args.founder_privkey}')

            # Get generated genesis block JSON
            with open(Path('genesis') / 'genesis_block.json') as first_file:
                genesis_block = json.load(first_file)

            gen_full_path = Path('genesis') / self.args.genesis_file_name

            # Get base genesis content JSON
            with open(gen_full_path) as second_file:
                genesis = json.load(second_file)

            genesis['abci_genesis'] = genesis_block

            with open(gen_full_path, 'w+') as gen_file:
                json.dump(genesis, gen_file)

        if self.args.copy_genesis:
            if not self.args.genesis_file_name:
                print('Genesis file name is required')
                return

            # REWORK to PATH
            genesis_path = os.path.normpath(os.path.join('genesis', self.args.genesis_file_name))
            target_path = c.COMETBFT_GENESIS
            os.system(f'cp {genesis_path} {target_path}')

        if self.args.validator_privkey:
            target_path = os.path.join(os.path.expanduser('~'), '.cometbft', 'config', 'priv_validator_key.json')

            keys = self.generate_keys()

            with open(target_path, 'w') as f:
                f.write(json.dumps(keys, indent=2))

        if self.args.prometheus:
            config['instrumentation']['prometheus'] = True

        print('Make sure that port 26657 is open for the REST API')
        print('Make sure that port 26656 is open for P2P Node communication')

        with open(self.CONFIG_PATH, 'w') as f:
            f.write(toml.dumps(config))
            print('Configuration updated')


if __name__ == '__main__':
    Configure().main()
