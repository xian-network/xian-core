import binascii
import marshal

from xian.constants import Constants as c
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


def convert_special_types(obj):
    """
    Recursively converts special types in dictionaries or lists.
    """
    if isinstance(obj, dict):
        return {k: convert_special_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_special_types(item) for item in obj]
    elif isinstance(obj, float):
        # Raise an error if floats are not allowed
        raise TypeError("Float values are not allowed due to precision loss. Use integers or strings.")
    elif isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


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
        if isinstance(s['value'], dict):
            s['value'] = convert_special_types(s['value'])

        client.raw_driver.set(s['key'], s['value'])

    for n in nonces:
        nonce_storage.set_nonce(n["key"], n["value"])

    for s in rewards:
        if isinstance(s['value'], dict):
            s['value'] = convert_special_types(s['value'])

        client.raw_driver.set(s['key'], s['value'])

    client.raw_driver.hard_apply(nanos)


async def store_genesis_block(client, nonce_storage, genesis_block: dict):
    if genesis_block is not None:
        apply_state_changes_from_block(client, nonce_storage, genesis_block)


def is_compiled_key(key):
    parts = key.split(".")
    return parts[1] == "__compiled__"


def get_latest_block_hash(driver):
    latest_hash = driver.get(c.LATEST_BLOCK_HASH_KEY)
    if latest_hash is None:
        return b""
    return latest_hash


def set_latest_block_hash(h, driver):
    driver.set(c.LATEST_BLOCK_HASH_KEY, h)


def get_latest_block_height(driver):
    h = driver.get(c.LATEST_BLOCK_HEIGHT_KEY, save=False)
    if h is None:
        return 0

    return int(h)


def set_latest_block_height(h, driver):
    driver.set(c.LATEST_BLOCK_HEIGHT_KEY, int(h))
