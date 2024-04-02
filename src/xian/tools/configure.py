from argparse import ArgumentParser
import toml
import os
import requests
import tarfile

"""
This is to configure the CometBFT node.
"""

class Configure:
    config_path = os.path.join(os.path.expanduser('~'), '.cometbft', 'config', 'config.toml')

    def __init__(self):
        self.parser = ArgumentParser(description='Configure')
        self.parser.add_argument('--seed-node', type=str, help='IP of the Seed Node', required=False)
        self.parser.add_argument('--moniker', type=str, help='Moniker/Name of your node', required=False)
        self.parser.add_argument('--allow-cors', type=bool, help='Allow CORS', required=False)
        self.parser.add_argument('--snapshot-url', type=str, help='URL of the snapshot', required=False)
        self.parser.add_argument('--copy-genesis', type=bool, help='Copy genesis file', required=False)
        self.parser.add_argument('--genesis-file-name', type=str, help='Genesis file name if copy-genesis is True e.g. genesis-testnet.json', required=False)
        self.parser.add_argument('--validator-privkey', type=str, help='Validator wallet private key 64 characters', required=False)
        # Chain ID is not neeeded anymore, bcz in Genesis block, we have chain_id
        # Snapshot should be a tar.gz file containing the data directory and xian directory
        # the priv_validator_state.json file that is in the snapshot should have
        # round and step set to 0
        # and signature, signbytes removed
        self.args = self.parser.parse_args()

    
    def download_and_extract(url, target_path):
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

    def main(self):
        # Make sure this is run in the tools directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        if not os.path.exists(self.config_path):
            print('Initialize cometbft first')
            return

        with open(self.config_path, 'r') as f:
            config = toml.load(f)

        if self.args.seed_node:
            info = requests.get(f'http://{self.args.seed_node}:26657/status')
            if info.status_code != 200:
                print('Seed node is not accessible')
                return
            id = info.json()['result']['node_info']['id']
            config['p2p']['seeds'] = f'{id}@{self.args.seed_node}:26656'

        if self.args.moniker:
            config['moniker'] = self.args.moniker

        if self.args.allow_cors:
            config['rpc']['cors_allowed_origins'] = ['*']

        if self.args.snapshot_url:
            # Download the snapshot
            self.download_and_extract(self.args.snapshot_url, os.path.join(os.path.expanduser('~'), '.cometbft'))

        if self.args.copy_genesis:
            if not self.args.genesis_file_name:
                print('Genesis file name is required')
                return
            # Copy the genesis file
            genesis_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'genesis', self.args.genesis_file_name)
            target_path = os.path.join(os.path.expanduser('~'), '.cometbft', 'config', 'genesis.json')
            os.system(f'cp {genesis_path} {target_path}')

        if self.args.validator_privkey:
            os.system(f'python3 validator_file_gen.py --validator_privkey {self.args.validator_privkey}')
            # Copy the priv_validator_key.json file
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'priv_validator_key.json')
            target_path = os.path.join(os.path.expanduser('~'), '.cometbft', 'config', 'priv_validator_key.json')
            os.system(f'cp {file_path} {target_path}')

        with open(self.config_path, 'w') as f:
            f.write(toml.dumps(config))

if __name__ == '__main__':
    configure = Configure()
    configure.main()