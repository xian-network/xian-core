from argparse import ArgumentParser
from contracting.client import ContractingClient
from contracting.db.driver import FSDriver, ContractDriver
from contracting.db.encoder import encode
from xian_py.wallet import Wallet
from pathlib import Path
import hashlib
import json


CONTRACT_DIR = Path.cwd().parent.absolute() / 'contracts'
MASTERNODE_PRICE = 100_000


def hash_block_data(hlc_timestamp: str, block_number: str, previous_block_hash: str) -> str:
    h = hashlib.sha3_256()
    h.update(f'{hlc_timestamp}{block_number}{previous_block_hash}'.encode())
    return h.hexdigest()


def hash_state_changes(state_changes: list) -> str:
    state_changes.sort(key=lambda x: x.get('key'))
    h = hashlib.sha3_256()
    # TODO: Adjust to f-string
    h.update('{}'.format(encode(state_changes).encode()).encode())
    return h.hexdigest()


def submit_from_config(client: ContractingClient):
    con_cfg_path = CONTRACT_DIR / 'contracts.json'

    with open(con_cfg_path) as f:
        con_cfg = json.load(f)

    for contract in con_cfg['contracts']:
        con_name = contract['name']
        con_ext = contract['extension']

        con_path = CONTRACT_DIR / con_name + con_ext

        with open(con_path) as f:
            code = f.read()

        if contract.get('submit_as') is not None:
            con_name = contract['submit_as']

        if client.get_contract(con_name) is None:
            client.submit(
                code,
                name=con_name,
                owner=contract['owner'],
                constructor_args=contract['constructor_args']
            )


def submit_masternodes(masternode_pk, client: ContractingClient):
    with open(CONTRACT_DIR / 'members.s.py') as f:
        code = f.read()

    if client.get_contract('masternodes') is None:
        client.submit(code, name='masternodes', owner='election_house', constructor_args={
            'initial_members': [masternode_pk],
            'candidate': 'elect_masternodes'
        })


def register_policies(client: ContractingClient):
    election_house = client.get_contract('election_house')

    policies = [
        'masternodes',
        'rewards',
        'stamp_cost',
        'dao'
    ]

    for policy in policies:
        if client.get_var(
            contract='election_house',
            variable='policies',
            arguments=[policy]
        ) is None:
            election_house.register_policy(contract=policy)


# TODO: Overwrite 'masternode_price' or set in some constants file
def setup_member_election(client: ContractingClient, masternode_price=100_000):
    with open(CONTRACT_DIR / 'elect_members.s.py') as f:
        code = f.read()

    if client.get_contract('elect_masternodes') is None:
        client.submit(code, name='elect_masternodes', constructor_args={
            'policy': 'masternodes',
            'cost': masternode_price,
        })


def build_genesis_block(founder_sk: str, masternode_pk: str):
    contracting = ContractingClient(driver=ContractDriver(FSDriver(root='/tmp/tmp_state')))
    contracting.set_submission_contract(filename=CONTRACT_DIR / 'submission.s.py', commit=False)

    submit_from_config(contracting)
    submit_masternodes(masternode_pk, contracting)
    register_policies(contracting)
    setup_member_election(contracting)

    block_number = "0"
    hlc_timestamp = '0000-00-00T00:00:00.000000000Z_0'
    previous_hash = '0' * 64

    block_hash = hash_block_data(hlc_timestamp, block_number, previous_hash)

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
    wallet = Wallet(seed=founder_sk)

    genesis_block['origin']['sender'] = wallet.public_key
    genesis_block['origin']['signature'] = wallet.sign_msg(
        hash_state_changes(genesis_block['genesis'])
    )

    return genesis_block


def main(founder_sk: str, masternode_pk: str = None, output_path: Path = None):

    output_path = Path(output_path) if output_path else Path.cwd()
    output_file = output_path.joinpath('genesis.json')

    print(f'Building genesis block...')
    genesis_block = build_genesis_block(founder_sk, masternode_pk)

    print(f'Loading genesis block...')
    with open(output_file) as f:
        genesis = json.load(f)

    print('Enrich genesis.json with genesis block data...')
    genesis['abci_genesis'] = encode(genesis_block)

    print(f'Saving genesis block to "{output_file}..."')
    with open(output_file, 'w') as f:
        f.write(genesis)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        '-m',
        '--masternode-pk',
        type=str,
        required=True,
        help="Masternode public key"
    )
    parser.add_argument(
        '-f',
        '--founder-sk',
        type=str,
        required=True,
        help="Founder's private key"
    )
    parser.add_argument(
        '-o',
        '--output-path',
        type=Path,
        default=None,
        help="The path to save the genesis block"
    )
    args = parser.parse_args()

    main(founder_sk=args.founder_sk, masternode_pk=args.masternode_pk, output_path=args.output_path or None)
