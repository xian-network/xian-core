import json
import hashlib

from pathlib import Path
from argparse import ArgumentParser
from contracting.storage.driver import Driver
from contracting.storage.encoder import encode
from xian_py.wallet import Wallet
from xian.utils.block import is_compiled_key, get_latest_block_height, get_latest_block_hash


def hash_genesis_block_state_changes(state_changes: list) -> str:
    # Convert all non-serializable objects in state_changes to a serializable format
    def serialize(obj):
        if isinstance(obj, bytes):
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
    hash = get_latest_block_hash()
    print('hash', hash)
    block_number = get_latest_block_height()

    genesis_block = {
        'hash': hash.hex(),
        'number': block_number,
        'origin': {
            'signature': '',
            'sender': ''
        },
        'genesis': [],
    }

    print("Populating run state...")

    nonces = [{'key': k[4:], 'value': v} for k, v in run_state.items() if k.startswith("__n.")]

    print('Populating genesis block...')
    for key, value in contract_state.items():
        if not is_compiled_key(key) and value is not None:
            genesis_block['genesis'].append({
                'key': key,
                'value': value
            })

    print('Sorting state changes...')
    genesis_block['genesis'] = sorted(genesis_block['genesis'], key=lambda d: d['key'])
    genesis_block['nonces'] = nonces

    if founder_sk:
        print('Signing state changes...')
        founders_wallet = Wallet(seed=bytes.fromhex(founder_sk))
        genesis_block['origin']['sender'] = founders_wallet.public_key
        genesis_block['origin']['signature'] = founders_wallet.sign_msg(hash_genesis_block_state_changes(genesis_block['genesis']))
    return genesis_block


def main(
    founder_sk: str,
    output_path: Path,
):
    output_path = output_path.joinpath('exported_state.json')

    contract_state, run_state = fetch_filebased_state()

    genesis_block = build_genesis_block(founder_sk, contract_state, run_state)

    print(f'Saving genesis block to "{output_path}"...')
    with open(output_path, 'w') as f:
        f.write(encode(genesis_block))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-k', '--key', type=str, required=False)
    parser.add_argument('--output-path', type=str, required=False)
    args = parser.parse_args()
    output_path = Path(args.output_path) if args.output_path is not None else Path.cwd()
    main(args.key, output_path)
