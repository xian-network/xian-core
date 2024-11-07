import binascii
import marshal
import json

from xian.constants import Constants as c
from contracting.storage.encoder import convert_dict
from loguru import logger

from google.protobuf.timestamp_pb2 import Timestamp
from datetime import datetime


def convert_cometbft_time_to_datetime(nanoseconds: int) -> datetime:
    timestamp = Timestamp()
    timestamp.FromNanoseconds(nanoseconds)
    return timestamp.ToDatetime()


def get_nanotime_from_block_time(timeobj) -> int:
    seconds = timeobj.seconds
    nanos = timeobj.nanos
    return (seconds * 1_000_000_000) + nanos


def compile_contract_from_source(s: dict):
    code = compile(s["value"], '', "exec")
    serialized_code = marshal.dumps(code)
    hexadecimal_string = binascii.hexlify(serialized_code).decode()
    return hexadecimal_string


def apply_state_changes_from_block(client, nonce_storage, block):
    state_changes = block.get('genesis', [])
    rewards = block.get('rewards', [])

    nanos = block.get('hlc_timestamp')
    nonces = block.get('nonces', [])

    for i, s in enumerate(state_changes):
        parts = s["key"].split(".")

        if parts[1] == "__code__":
            logger.info(f'Processing contract: {parts[0]}')
            compiled_code = compile_contract_from_source(s)
            client.raw_driver.set(f"{parts[0]}.__compiled__", compiled_code)
        if type(s['value']) is dict:
            s['value'] = convert_dict(s['value'])

        client.raw_driver.set(s['key'], s['value'])

    for n in nonces:
        nonce_storage.set_nonce(n["key"], n["value"])

    for s in rewards:
        if type(s['value']) is dict:
            s['value'] = convert_dict(s['value'])

        client.raw_driver.set(s['key'], s['value'])

    client.raw_driver.hard_apply(nanos)


async def store_genesis_block(client, nonce_storage, genesis_block: dict):
    if genesis_block is not None:
        apply_state_changes_from_block(client, nonce_storage, genesis_block)


def is_compiled_key(key):
    parts = key.split(".")
    if parts[1] == "__compiled__":
        return True
    return False

def create_latest_block_json_if_not_exists():
    try:
        with open(f"{c.STORAGE_HOME}/__latest_block.json", "x") as f:
            json.dump({"hash": "", "height": 0}, f)
    except FileExistsError:
        pass


def get_latest_block_hash():
    # Get the latest block hash from the json file
    create_latest_block_json_if_not_exists()
    try:
        with open(f"{c.STORAGE_HOME}/__latest_block.json", "r") as f:
            latest_block = json.load(f)
            latest_hash = bytes.fromhex(latest_block.get("hash"))
    except FileNotFoundError:
        raise Exception("__latest_block.json not found")
    except json.JSONDecodeError:
        raise Exception("Error decoding __latest_block.json")

    return latest_hash


def set_latest_block_hash(h):
    # Set the latest block hash in the json file
    create_latest_block_json_if_not_exists()
    try:
        with open(f"{c.STORAGE_HOME}/__latest_block.json", "r") as f:
            latest_block = json.load(f)
        
        # Update the hash while keeping the height intact
        latest_block["hash"] = h.hex()

        with open(f"{c.STORAGE_HOME}/__latest_block.json", "w") as f:
            json.dump(latest_block, f)
    except FileNotFoundError:
        raise Exception("__latest_block.json not found")
    except json.JSONDecodeError:
        raise Exception("Error decoding __latest_block.json")


def get_latest_block_height():
    # Get the latest block height from the json file
    create_latest_block_json_if_not_exists()
    try:
        with open(f"{c.STORAGE_HOME}/__latest_block.json", "r") as f:
            latest_block = json.load(f)
            latest_height = latest_block.get("height")
    except FileNotFoundError:
        raise Exception("__latest_block.json not found")
    except json.JSONDecodeError:
        raise Exception("Error decoding __latest_block.json")

    return latest_height


def set_latest_block_height(h):
    # Set the latest block height in the json file
    create_latest_block_json_if_not_exists()
    try:
        with open(f"{c.STORAGE_HOME}/__latest_block.json", "r") as f:
            latest_block = json.load(f)
        
        # Update the height while keeping the hash intact
        latest_block["height"] = h

        with open(f"{c.STORAGE_HOME}/__latest_block.json", "w") as f:
            json.dump(latest_block, f)
    except FileNotFoundError:
        raise Exception("__latest_block.json not found")
    except json.JSONDecodeError:
        raise Exception("Error decoding __latest_block.json")