from argparse import ArgumentParser
import toml
import os
import requests

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
        # Chain ID is not neeeded anymore, bcz in Genesis block, we have chain_id
        self.args = self.parser.parse_args()

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

        with open(self.config_path, 'w') as f:
            f.write(toml.dumps(config))

if __name__ == '__main__':
    configure = Configure()
    configure.main()