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


        with open(self.config_path, 'w') as f:
            f.write(toml.dumps(config))

if __name__ == '__main__':
    configure = Configure()
    configure.main()