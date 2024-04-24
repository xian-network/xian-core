import json
import hashlib
from pathlib import Path
from argparse import ArgumentParser
from contracting.storage.driver import Driver
from contracting.storage.encoder import encode
from xian_py.wallet import Wallet


def hash_genesis_block_state_changes(state_changes: list) -> str:
    # Convert all non-serializable objects in state_changes to a serializable format
    def serialize(obj):
        if isinstance(obj, bytes):
            print(obj)
            return obj.hex()  # Convert bytes to hex string
        # return str(obj)  # Fallback: convert other types to string

    h = hashlib.sha3_256()

    # Use the default argument of json.dumps to specify the custom serializer
    h.update(json.dumps(state_changes, default=serialize).encode('utf-8'))
    return h.hexdigest()


def should_ignore(key, ignore_keys):
    for ik in ignore_keys:
        if key.startswith(ik):
            return True

    return False


def fetch_filebased_state():
    print('Migrating existing file-based state...')
    driver = Driver()
    contract_state = driver.get_all_contract_state()
    run_state = driver.get_run_state()
    return contract_state, run_state


def build_genesis_block(founder_sk: str, contract_state: dict, run_state: dict):
    genesis_block = {
        'hash': "0" * 64,
        'number': "0",
        'previous': "0" * 64,
        'origin': {
            'signature': '',
            'sender': ''
        },
        'genesis': [],
    }

    print("Populating run state...")
    genesis_block["hash"] = run_state["__latest_block.hash"].hex()
    genesis_block["number"] = run_state["__latest_block.height"]

    print('Populating genesis block...')
    for key, value in contract_state.items():
        genesis_block['genesis'].append({
            'key': key,
            'value': value
        })

    print('Sorting state changes...')
    genesis_block['genesis'] = sorted(genesis_block['genesis'], key=lambda d: d['key'])

    print('Signing state changes...')
    founders_wallet = Wallet(seed=bytes.fromhex(founder_sk))
    genesis_block['origin']['sender'] = founders_wallet.public_key
    genesis_block['origin']['signature'] = founders_wallet.sign_msg(hash_genesis_block_state_changes(genesis_block['genesis']))
    return genesis_block


def main(
    founder_sk: str,
    output_path: Path,
):
    output_path = output_path.joinpath('genesis_block.json')

    contract_state, run_state = fetch_filebased_state()

    genesis_block = build_genesis_block(founder_sk, contract_state, run_state)

    print(f'Saving genesis block to "{output_path}"...')
    with open(output_path, 'w') as f:
        f.write(encode(genesis_block))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-k', '--key', type=str, required=True)
    parser.add_argument('--output-path', type=str, required=True)
    args = parser.parse_args()
    output_path = Path(args.output_path)
    main(args.key, output_path)
