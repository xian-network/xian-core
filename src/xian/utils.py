import binascii
import json
import struct
import toml
import nacl
import nacl.encoding
import nacl.signing
import hashlib
import marshal
import binascii

import xian.constants as c

from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.stdlib.bridge.time import Datetime
from contracting.storage.encoder import encode, decode, convert_dict
from xian.exceptions import TransactionException
from xian.formatting import contract_name_is_formatted, TRANSACTION_PAYLOAD_RULES, TRANSACTION_RULES
from abci.utils import get_logger


# Z85CHARS is the base 85 symbol table
Z85CHARS = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#"
# Z85MAP maps integers in [0,84] to the appropriate character in Z85CHARS
Z85MAP = {c: idx for idx, c in enumerate(Z85CHARS)}

_85s = [85**i for i in range(5)][::-1]

# Logging
logger = get_logger(__name__)


def z85_encode(rawbytes):
    """encode raw bytes into Z85"""
    # Accepts only byte arrays bounded to 4 bytes
    if len(rawbytes) % 4:
        raise ValueError("length must be multiple of 4, not %i" % len(rawbytes))

    nvalues = len(rawbytes) / 4

    values = struct.unpack(">%dI" % nvalues, rawbytes)
    encoded = []
    for v in values:
        for offset in _85s:
            encoded.append(Z85CHARS[(v // offset) % 85])

    return bytes(encoded)


def z85_decode(z85bytes):
    """decode Z85 bytes to raw bytes, accepts ASCII string"""
    if isinstance(z85bytes, str):
        try:
            z85bytes = z85bytes.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("string argument should contain only ASCII characters")

    if len(z85bytes) % 5:
        raise ValueError("Z85 length must be multiple of 5, not %i" % len(z85bytes))

    nvalues = len(z85bytes) / 5
    values = []
    for i in range(0, len(z85bytes), 5):
        value = 0
        for j, offset in enumerate(_85s):
            value += Z85MAP[z85bytes[i + j]] * offset
        values.append(value)
    return struct.pack(">%dI" % nvalues, *values)


def verify(vk: str, msg: str, signature: str):
    vk = bytes.fromhex(vk)
    msg = msg.encode()
    signature = bytes.fromhex(signature)

    vk = nacl.signing.VerifyKey(vk)
    try:
        vk.verify(msg, signature)
    except nacl.exceptions.BadSignatureError:
        return False
    return True


def hash_list(obj: list) -> bytes:
    h = hashlib.sha3_256()
    str = "".join(obj)
    encoded_tx = encode(str).encode()
    h.update(encoded_tx)
    return h.hexdigest().encode("utf-8")


def hash_from_rewards(rewards):
    h = hashlib.sha3_256()
    encoded_rewards = encode(rewards).encode()
    h.update(encoded_rewards)
    return h.hexdigest()


def encode_int(value):
    return struct.pack(">I", value)


def encode_number(value):
    return struct.pack(">d", value)


def encode_str(value):
    return value.encode("utf-8")


def decode_number(string):
    return struct.unpack(">I", string)[0]


def decode_str(string):
    return string.decode("utf-8")


def decode_json(raw):
    return json.loads(raw.decode("utf-8"))


def decode_transaction_bytes(raw):
    tx_bytes = raw
    tx_hex = tx_bytes.decode("utf-8")
    tx_decoded_bytes = bytes.fromhex(tx_hex)
    tx_str = tx_decoded_bytes.decode("utf-8")
    tx_json = json.loads(tx_str)
    return tx_json


def unpack_transaction(tx):
    timestamp = tx["metadata"].get("timestamp", None)
    if timestamp:
        print("Please remove timestamp from metadata")
    chain_id = tx["payload"].get("chain_id", "")
    if not chain_id:
        print("Please add chain_id to payload")

    sender = tx["payload"]["sender"]
    signature = tx["metadata"]["signature"]
    tx_for_verification = {
        "chain_id": chain_id,
        "contract": tx["payload"]["contract"],
        "function": tx["payload"]["function"],
        "kwargs": tx["payload"]["kwargs"],
        "nonce": tx["payload"]["nonce"],
        "sender": tx["payload"]["sender"],
        "stamps_supplied": tx["payload"]["stamps_supplied"],
    }
    tx_for_verification = encode(decode(encode(tx_for_verification)))
    return sender, signature, tx_for_verification


def get_nanotime_from_block_time(timeobj) -> int:
    seconds = timeobj.seconds
    nanos = timeobj.nanos
    return (seconds * 1_000_000_000) + nanos


def convert_binary_to_hex(binary_data):
    try:
        return binascii.hexlify(binary_data).decode()
    except UnicodeDecodeError as e:
        logger.error(f"The binary data could not be decoded with UTF-8 encoding: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise


def load_tendermint_config():
    if not (c.TENDERMINT_HOME.exists() and c.TENDERMINT_HOME.is_dir()):
        raise FileNotFoundError("You must initialize Tendermint first")
    if not (c.TENDERMINT_CONFIG.exists() and c.TENDERMINT_CONFIG.is_file()):
        raise FileNotFoundError(f"File not found: {c.TENDERMINT_CONFIG}")

    return toml.load(c.TENDERMINT_CONFIG)


def load_genesis_data():
    if not (c.TENDERMINT_GENESIS.exists() and c.TENDERMINT_GENESIS.is_file()):
        raise FileNotFoundError(f"File not found: {c.TENDERMINT_GENESIS}")

    with open(c.TENDERMINT_GENESIS, "r") as file:
        return json.load(file)


def stringify_decimals(obj):
    target_class = ContractingDecimal
    try:
        if isinstance(obj, target_class):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: stringify_decimals(val) for key, val in obj.items()}
        elif isinstance(obj, list):
            return [stringify_decimals(elem) for elem in obj]
        elif isinstance(obj, Datetime):
            return str(obj)
        elif isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return str(obj)
        else:
            return obj
    except:
        return ""
    

def format_dictionary(d: dict) -> dict:
    for k, v in d.items():
        assert type(k) == str, 'Non-string key types not allowed.'
        if type(v) == list:
            for i in range(len(v)):
                if isinstance(v[i], dict):
                    v[i] = format_dictionary(v[i])
        elif isinstance(v, dict):
            d[k] = format_dictionary(v)
    return {k: v for k, v in sorted(d.items())}

def recurse_rules(d: dict, rule: dict):
        if callable(rule):
            return rule(d)

        for key, subrule in rule.items():
            arg = d[key]

            if type(arg) == dict:
                if not recurse_rules(arg, subrule):
                    return False

            elif type(arg) == list:
                for a in arg:
                    if not recurse_rules(a, subrule):
                        return False

            elif callable(subrule):
                if not subrule(arg):
                    return False

        return True

def tx_hash_from_tx(tx):
    h = hashlib.sha3_256()
    tx_dict = format_dictionary(tx)
    encoded_tx = encode(tx_dict).encode()
    h.update(encoded_tx)
    return h.hexdigest()


def hash_from_validator_updates(validator_updates):
    h = hashlib.sha3_256()
    encoded_validator_updates = str(validator_updates).encode()
    h.update(encoded_validator_updates)
    return h.hexdigest()


def hash_from_rewards(rewards):
    h = hashlib.sha3_256()
    encoded_rewards = encode(rewards).encode()
    h.update(encoded_rewards)
    return h.hexdigest()

def dict_has_keys(d: dict, keys: set):
        key_set = set(d.keys())
        return len(keys ^ key_set) == 0

def check_enough_stamps(
        balance: object,
        stamps_per_tau: object,
        stamps_supplied: object,
        contract: object = None,
        function: object = None,
        amount: object = 0
):

    if balance * stamps_per_tau < stamps_supplied:
        raise TransactionException('Transaction sender has too few stamps for this transaction')

    # Prevent people from sending their entire balances for free by checking if that is what they are doing.
    if contract == "currency" and function == "transfer":

        # If you have less than 2 transactions worth of tau after trying to send your amount, fail.
        if ((balance - amount) * stamps_per_tau) / 6 < 2:
            raise TransactionException('Transaction sender has too few stamps for this transaction')

def check_format(d: dict, rule: dict):
        expected_keys = set(rule.keys())

        if not dict_has_keys(d, expected_keys):
            raise TransactionException("Transaction has unexpected or missing keys")
        if not recurse_rules(d, rule):
            raise TransactionException("Transaction has wrongly formatted dictionary")

def check_tx_keys(tx):
    metadata = tx.get("metadata")

    if not metadata:
        raise TransactionException("Metadata is missing")
    if len(metadata.keys()) != 1:
        raise TransactionException("Wrong number of metadata entries")

    payload = tx.get("payload")

    if not payload:
        raise TransactionException("Payload is missing")
    if not payload["sender"]:
        raise TransactionException("Payload key 'sender' is missing")
    if not payload["contract"]:
        raise TransactionException("Payload key 'contract' is missing")
    if not payload["function"]:
        raise TransactionException("Payload key 'function' is missing")
    if not payload["stamps_supplied"]:
        raise TransactionException("Payload key 'stamps_supplied' is missing")

    keys = list(payload.keys())
    keys_are_valid = list(
        map(lambda key: key in keys, list(TRANSACTION_PAYLOAD_RULES.keys()))
    )

    if not all(keys_are_valid) and len(keys) == len(list(TRANSACTION_PAYLOAD_RULES.keys())):
        raise TransactionException("Payload keys are not valid")

def check_tx_formatting(tx: dict):
    check_tx_keys(tx)
    check_format(tx, TRANSACTION_RULES)

    if not verify(
            tx["payload"]["sender"], encode(tx["payload"]), tx["metadata"]["signature"]
    ):
        raise TransactionException('Transaction is not signed by the sender')
    
def check_contract_name(contract, function, name):
        if (
                contract == "submission"
                and function == "submit_contract"
                and (len(name) > 255 or not contract_name_is_formatted(name))
        ):
            raise TransactionException('Transaction contract name is invalid')


def validate_transaction(client, nonce_storage, tx):
        # Check transaction formatting
        check_tx_formatting(tx)

        # Check if nonce is greater than the current nonce
        nonce_storage.check_nonce(tx)

        # Get the senders balance and the current stamp rate
        try:
            balance = client.get_var(
                contract="currency",
                variable="balances",
                arguments=[tx["payload"]["sender"]],
                mark=False
            )
        except Exception as e:
            raise TransactionException(f"Failed to retrieve 'currency' balance for sender: {e}")

        try:
            stamp_rate = client.get_var(
                contract="stamp_cost",
                variable="S",
                arguments=["value"],
                mark=False
            )
        except Exception as e:
            raise TransactionException(f"Failed to get stamp cost: {e}")

        contract = tx["payload"]["contract"]
        func = tx["payload"]["function"]
        stamps_supplied = tx["payload"]["stamps_supplied"]

        if stamps_supplied is None:
            stamps_supplied = 0

        if stamp_rate is None:
            stamp_rate = 0

        if balance is None:
            balance = 0

        # Get how much they are sending
        amount = tx["payload"]["kwargs"].get("amount")
        if amount is None:
            amount = 0

        # Check if they have enough stamps for the operation
        check_enough_stamps(
            balance,
            stamp_rate,
            stamps_supplied,
            contract=contract,
            function=func,
            amount=amount,
        )

        # Check if contract name is valid
        name = tx["payload"]["kwargs"].get("name")
        check_contract_name(contract, func, name)


def recompile_contract_from_source(s: dict):
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
            state_changes[i + 1]["value"]["__bytes__"] = recompile_contract_from_source(s)
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

    if type(h) == ContractingDecimal:
        h = int(h._d)

    return int(h)


def set_latest_block_height(h, driver):
    driver.set(c.LATEST_BLOCK_HEIGHT_KEY, int(h))


def is_compiled_key(key):
    parts = key.split(".")
    if parts[1] == "__compiled__":
        return True
    return False
