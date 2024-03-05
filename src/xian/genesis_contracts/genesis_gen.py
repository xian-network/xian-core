from argparse import ArgumentParser
from contracting.client import ContractingClient
from contracting.db.driver import FSDriver, ContractDriver, CODE_KEY, COMPILED_KEY, OWNER_KEY, TIME_KEY, DEVELOPER_KEY
from contracting.db.encoder import encode
from xian_py.wallet import Wallet
from pathlib import Path
import hashlib
import json

GENESIS_CONTRACTS = ['submission', 'currency', 'election_house', 'stamp_cost', 'rewards', 'foundation', 'masternodes', 'elect_masternodes']
GENESIS_CONTRACTS_KEYS = [contract + '.' + key for key in [CODE_KEY, COMPILED_KEY, OWNER_KEY, TIME_KEY, DEVELOPER_KEY] for contract in GENESIS_CONTRACTS]
GENESIS_BLOCK_NUMBER = "0"
GENESIS_HLC_TIMESTAMP = '0000-00-00T00:00:00.000000000Z_0'
GENESIS_PREVIOUS_HASH = '0' * 64
TMP_STATE_PATH = Path('/tmp/tmp_state')

def block_hash_from_block(hlc_timestamp: str, block_number: str, previous_block_hash: str) -> str:
    h = hashlib.sha3_256()
    h.update('{}{}{}'.format(hlc_timestamp, block_number, previous_block_hash).encode())
    return h.hexdigest()

def hash_genesis_block_state_changes(state_changes: list) -> str:
    state_changes.sort(key=lambda x: x.get('key'))
    h = hashlib.sha3_256()
    h.update('{}'.format(encode(state_changes).encode()).encode())
    return h.hexdigest()

def submit_from_genesis_json_file(client: ContractingClient):
    with open(Path.cwd().joinpath('genesis.json')) as f:
        genesis = json.load(f)

    for contract in genesis['contracts']:
        c_filepath = Path.cwd().joinpath('genesis').joinpath(contract['name'] + '.s.py')

        with open(c_filepath) as f:
            code = f.read()

        contract_name = contract['name']
        if contract.get('submit_as') is not None:
            contract_name = contract['submit_as']

        if client.get_contract(contract_name) is None:
            client.submit(code, name=contract_name, owner=contract['owner'],
                          constructor_args=contract['constructor_args'])

def setup_member_contracts(initial_masternode, client: ContractingClient):
    current_dir = Path.cwd()
    genesis_folder = current_dir.joinpath('genesis')
    members = genesis_folder.joinpath('members.s.py')

    with open(members) as f:
        code = f.read()

    if client.get_contract('masternodes') is None:
        client.submit(code, name='masternodes', owner='election_house', constructor_args={
            'initial_members': [initial_masternode],
            'candidate': 'elect_masternodes'
        })

def register_policies(client: ContractingClient):
    # add to election house
    election_house = client.get_contract('election_house')

    policies_to_register = [
        'masternodes',
        'rewards',
        'stamp_cost',
        'dao'
    ]

    for policy in policies_to_register:
        if client.get_var(
            contract='election_house',
            variable='policies',
            arguments=[policy]
        ) is None:
            election_house.register_policy(contract=policy)

def setup_member_election_contracts(client: ContractingClient, masternode_price=500_000, root=Path.cwd()):
    elect_members = root.joinpath('genesis').joinpath('elect_members.s.py')

    with open(elect_members) as f:
        code = f.read()

    if client.get_contract('elect_masternodes') is None:
        client.submit(code, name='elect_masternodes', constructor_args={
            'policy': 'masternodes',
            'cost': masternode_price,
        })


def build_block(founder_sk: str, initial_masternode: str):
    state_changes = {}
    contracting_client = ContractingClient(driver=ContractDriver(FSDriver(root=TMP_STATE_PATH)))
    contracting_client.set_submission_contract(filename=Path.cwd().joinpath('submission.s.py'), commit=False)

    submit_from_genesis_json_file(contracting_client)
    setup_member_contracts(initial_masternode, contracting_client)
    register_policies(contracting_client)
    setup_member_election_contracts(contracting_client)

    state_changes.update(contracting_client.raw_driver.pending_writes)
    contracting_client.raw_driver.flush()
    
    data = {k: v for k, v in state_changes.items() if v is not None}

    genesis_block = {
        'hash': block_hash_from_block(GENESIS_HLC_TIMESTAMP, GENESIS_BLOCK_NUMBER, GENESIS_PREVIOUS_HASH),
        'number': GENESIS_BLOCK_NUMBER,
        'hlc_timestamp': GENESIS_HLC_TIMESTAMP,
        'previous': GENESIS_PREVIOUS_HASH,
        'genesis': [],
        'origin': {
            'signature': '',
            'sender': ''
        }
    }

    for key, value in data.items():
        genesis_block['genesis'].append({
            'key': key,
            'value': value
        })

    print('Signing genesis block with founder\'s wallet...')
    founders_wallet = Wallet(seed=founder_sk)
    genesis_block['origin']['sender'] = founders_wallet.public_key
    genesis_block['origin']['signature'] = founders_wallet.sign_msg(hash_genesis_block_state_changes(genesis_block['genesis']))

    return genesis_block

def main(
    founder_sk: str,
    output_path: Path = None,
    initial_masternode: str = None,
):
    if output_path is None:
        output_path = Path.cwd()
    else:
        output_path = Path(output_path)
    output_path = output_path.joinpath('genesis_block.json')
    assert not output_path.is_file(), f'"{output_path}" already exist'

    genesis_block = build_block(founder_sk, initial_masternode)

    print(f'Saving genesis block to "{output_path}"')
    with open(output_path, 'w') as f:
        f.write(encode(genesis_block))

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-n', '--initial-masternode-address', type=str, required=True, help='The initial masternode address')
    parser.add_argument('-k', '--key', type=str, required=True, help='The founder\'s private key')
    parser.add_argument('-o', '--output-path', type=Path, default=None, help='The path to save the genesis block')
    args = parser.parse_args()

    main(founder_sk=args.key, output_path=args.output_path or None, initial_masternode=args.initial_masternode_address)