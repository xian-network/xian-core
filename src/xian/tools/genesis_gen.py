from argparse import ArgumentParser
from xian.utils.block import is_compiled_key
from contracting.client import ContractingClient
from contracting.storage.driver import Driver
from contracting.storage.encoder import encode
from xian_py.wallet import Wallet
from pathlib import Path

import hashlib
import json
import re

"""
Generate genesis_block.json file for CometBFT genesis.json
Usage : 
    Run from an environment where xian-contracting & xian-core are installed.
    Xian state must be blank. You may wish to temporarily rename .cometbft and call `make init` before hand to achieve this.
    `python genesis_gen.py --founder-privkey "your_founder_private_key" --output-path "path_to_output_file" --genesis-to-update "path_to_existing_genesis_file" --network "devnet|stagenet|etc"`
"""


class GenesisGen:
    CONTRACT_DIR = Path.cwd() / 'genesis' / 'contracts'

    def __init__(self):
        parser = ArgumentParser(description='Genesis File Generator')
        parser.add_argument(
            '--founder-privkey',
            type=str,
            required=True,
            help="Founder's private key"
        )
        parser.add_argument(
            '--output-path',
            type=Path,
            default=None,
            help="Path to save generated file"
        )
        parser.add_argument(
            '--network',
            type=str,
            required=False,
            default="devnet",
            help='Network to generate genesis for. Maps to a config file, e.g. genesis/contracts/contracts_<network>.json'
        )
        parser.add_argument(
            '--genesis-to-update',
            type=Path,
            required=False,
            default=None,
            help='Path to existing cometbft genesis file to update the abci_genesis on.'
        )
        self.args = parser.parse_args()

    def hash_block_data(self, hlc_timestamp: str, block_number: str, previous_block_hash: str) -> str:
        h = hashlib.sha3_256()
        h.update(f'{hlc_timestamp}{block_number}{previous_block_hash}'.encode())
        return h.hexdigest()

    def hash_state_changes(self, state_changes: list) -> str:
        state_changes.sort(key=lambda x: x.get('key'))
        h = hashlib.sha3_256()
        h.update(f'{encode(state_changes).encode()}'.encode())
        return h.hexdigest()

    def replace_arg(self, arg: str, values: dict):
        result = re.search('%%(.*)%%', arg)

        if result:
            new_value = values[result.group(1)]
            return arg.replace(result.group(), new_value)
        else:
            return arg

    def build_genesis(self, founder_privkey: str):
        contracting = ContractingClient(driver=Driver())
        contracting.set_submission_contract(commit=False)

        con_cfg_path = self.CONTRACT_DIR / f'contracts_{self.args.network}.json'

        with open(con_cfg_path) as f:
            con_cfg = json.load(f)

        con_ext = con_cfg['extension']

        # Process contracts in contracts.json
        for contract in con_cfg['contracts']:
            con_name = contract['name']
            con_path = self.CONTRACT_DIR / (con_name + con_ext)

            with open(con_path) as f:
                code = f.read()
            if contract.get('submit_as') is not None:
                con_name = contract['submit_as']

            # Replace constructor argument values if needed
            if contract['constructor_args'] is not None:
                for k, v in contract['constructor_args'].items():
                    if type(v) is str:
                        contract['constructor_args'][k] = self.replace_arg(v, locals())
                    elif type(v) is list:
                        for i, s in enumerate(v):
                            if type(s) is str:
                                v[i] = self.replace_arg(s, locals())
                                
            if contracting.get_contract(con_name) is None:
                contracting.submit(
                    code,
                    name=con_name,
                    owner=contract['owner'],
                    constructor_args=contract['constructor_args']
                )

        block_number = "0"
        hlc_timestamp = '0000-00-00T00:00:00.000000000Z_0'
        previous_hash = '0' * 64

        block_hash = self.hash_block_data(hlc_timestamp, block_number, previous_hash)

        genesis_block = {
            'hash': block_hash,
            'number': block_number,
            'genesis': [],
            'origin': {
                'signature': '',
                'sender': ''
            }
        }

        state_changes = {}
        state_changes.update(contracting.raw_driver.pending_writes)

        data = {k: v for k, v in state_changes.items() if v is not None}

        for key, value in data.items():
            if not is_compiled_key(key):
                genesis_block['genesis'].append({
                    'key': key,
                    'value': value
                })

        # Signing genesis block with founder's wallet
        wallet = Wallet(seed=founder_privkey)

        genesis_block['origin']['sender'] = wallet.public_key
        genesis_block['origin']['signature'] = wallet.sign_msg(
            self.hash_state_changes(genesis_block['genesis'])
        )

        return genesis_block

    def main(self):
        output_path = self.args.output_path if self.args.output_path else (Path.cwd() / 'genesis')
        output_file = output_path / Path('genesis_block.json')

        genesis = self.build_genesis(self.args.founder_privkey)

        with open(output_file, 'w') as f:
            f.write(encode(genesis))

        if self.args.genesis_to_update:
            with open(self.args.genesis_to_update, 'r') as f:
                existing_genesis = json.load(f)

            existing_genesis['abci_genesis'] = genesis
            with open(self.args.genesis_to_update, 'w') as f:
                f.write(encode(existing_genesis))


if __name__ == '__main__':
    GenesisGen().main()
