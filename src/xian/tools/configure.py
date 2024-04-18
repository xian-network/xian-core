import requests
import tarfile
import toml
import os
import json
import hashlib


from time import sleep
from argparse import ArgumentParser
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder, Base64Encoder

"""
This is to configure the CometBFT node.
"""


class Configure:
    config_path = os.path.join(os.path.expanduser('~'), '.cometbft', 'config', 'config.toml')

    def __init__(self):
        self.parser = ArgumentParser(description='Configure')
        self.parser.add_argument('--seed-node', type=str, help='IP of the Seed Node e.g. 91.108.112.184 (without port, but 26657 and 26656 needs to be open)', required=False)
        self.parser.add_argument('--seed-node-address', type=str, help='If the full seed node address is provided w/o port e.g. ', required=False)
        self.parser.add_argument('--moniker', type=str, help='Moniker/Name of your node', required=True)
        self.parser.add_argument('--allow-cors', type=bool, help='Allow CORS', required=False, default=True)
        self.parser.add_argument('--snapshot-url', type=str, help='URL of the snapshot e.g. https://github.com/xian-network/snapshots/raw/main/testnet-2024-04-02.tar (tar.gz file)', required=False)
        self.parser.add_argument('--copy-genesis', type=bool, help='Copy genesis file', required=True, default=True)
        self.parser.add_argument('--genesis-file-name', type=str, help='Genesis file name if copy-genesis is True e.g. genesis-testnet.json', required=True, default="genesis-testnet.json")
        self.parser.add_argument('--validator-privkey', type=str, help='Validator wallet private key 64 characters', required=True)
        self.parser.add_argument('--prometheus', type=bool, help='Enable Prometheus', required=False, default=True)
        # Chain ID is not neeeded anymore, bcz in Genesis block, we have chain_id
        # Snapshot should be a tar.gz file containing the data directory and xian directory
        # the priv_validator_state.json file that is in the snapshot should have
        # round and step set to 0
        # and signature, signbytes removed
        self.args = self.parser.parse_args()
    
    def download_and_extract(self, url, target_path):
        # Download the file from the URL
        response = requests.get(url)
        filename = url.split('/')[-1]  # Assumes the URL ends with the filename
        tar_path = os.path.join(target_path, filename)
        
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
        
        if not os.path.exists(self.config_path):
            print('Initialize CometBFT first')
            return

        with open(self.config_path, 'r') as f:
            config = toml.load(f)

        config['consensus']['create_empty_blocks'] = False

        # If seed node address is provided, use it
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

        if self.args.moniker:
            config['moniker'] = self.args.moniker

        if self.args.allow_cors:
            config['rpc']['cors_allowed_origins'] = ['*']

        config['consensus']['create_empty_blocks'] = False

        if self.args.snapshot_url:
            # If data directory exists, delete it
            data_dir = os.path.join(os.path.expanduser('~'), '.cometbft', 'data')
            if os.path.exists(data_dir):
                os.system(f'rm -rf {data_dir}')
            # If xian directory exists, delete it
            xian_dir = os.path.join(os.path.expanduser('~'), '.cometbft', 'xian')
            if os.path.exists(xian_dir):
                os.system(f'rm -rf {xian_dir}')
            # Download the snapshot
            self.download_and_extract(self.args.snapshot_url, os.path.join(os.path.expanduser('~'), '.cometbft'))

        if self.args.copy_genesis:
            if not self.args.genesis_file_name:
                print('Genesis file name is required')
                return
            # Go up one directory to get to the genesis file
            genesis_path = os.path.normpath(os.path.join('..', 'genesis', self.args.genesis_file_name))
            target_path = os.path.join(os.path.expanduser('~'), '.cometbft', 'config', 'genesis.json')
            os.system(f'cp {genesis_path} {target_path}')

        if self.args.validator_privkey:
            target_path = os.path.join(os.path.expanduser('~'), '.cometbft', 'config', 'priv_validator_key_1.json')

            keys = self.generate_keys()

            with open(target_path, 'w') as f:
                f.write(json.dumps(keys, indent=2))


        if self.args.prometheus:
            config['instrumentation']['prometheus'] = True
            print('Make sure that port 26660 is open for Prometheus')
        print('Make sure that port 26657 is open for the REST API')
        print('Make sure that port 26656 is open for P2P Node communication')

        with open(self.config_path, 'w') as f:
            f.write(toml.dumps(config))
            print('Configuration updated')


if __name__ == '__main__':
    configure = Configure()
    configure.main()
