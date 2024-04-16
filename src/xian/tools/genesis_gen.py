from argparse import ArgumentParser
from contracting.client import ContractingClient
from contracting.db.driver import FSDriver, ContractDriver
from contracting.db.encoder import encode
from xian_py.wallet import Wallet
from pathlib import Path
import hashlib
import json
import re

"""
Generate genesis_block.json file for CometBFT genesis.json
"""


class GenesisGen:
    CONTRACT_DIR = Path.cwd() / 'src' / 'xian' / 'genesis' / 'contracts'

    def __init__(self):
        parser = ArgumentParser(description='Genesis File Generator')
        parser.add_argument(
            '--validator-pubkey',
            type=str,
            required=True,
            help="Validator's public key"
        )
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

    def replace_arg(selg, arg: str, values: dict):
        result = re.search('%%(.*)%%', arg)

        if result:
            new_value = values[result.group(1)]
            return arg.replace(result.group(), new_value)
        else:
            return arg

    def build_genesis(self, founder_privkey: str, validator_pubkey: str):
        contracting = ContractingClient(driver=ContractDriver(FSDriver(root='/tmp/tmp_state')))
        contracting.set_submission_contract(commit=False)

        con_cfg_path = self.CONTRACT_DIR / 'contracts.json'

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

        # Set policies
        election_house = contracting.get_contract('election_house')

        policies = [
            'masternodes',
            'rewards',
            'stamp_cost',
            'dao'
        ]

        for policy in policies:
            if contracting.get_var(
                contract='election_house',
                variable='policies',
                arguments=[policy]
            ) is None:
                election_house.register_policy(contract=policy)

        block_number = "0"
        hlc_timestamp = '0000-00-00T00:00:00.000000000Z_0'
        previous_hash = '0' * 64

        block_hash = self.hash_block_data(hlc_timestamp, block_number, previous_hash)

        genesis_block = {
            'hash': block_hash,
            'number': block_number,
            'hlc_timestamp': hlc_timestamp,
            'previous': previous_hash,
            'genesis': [],
            'origin': {
                'signature': '',
                'sender': ''
            }
        }

        state_changes = {}
        state_changes.update(contracting.raw_driver.pending_writes)

        contracting.raw_driver.flush()

        data = {k: v for k, v in state_changes.items() if v is not None}

        for key, value in data.items():
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
        output_path = Path(self.args.output_path) if self.args.output_path else Path.cwd()
        output_file = output_path / Path('genesis_block.json')

        genesis = self.build_genesis(self.args.founder_privkey, self.args.validator_pubkey)
        print(f'Saving genesis block to {output_file}')

        with open(output_file, 'w') as f:
            f.write(encode(genesis))


if __name__ == '__main__':
    GenesisGen().main()
