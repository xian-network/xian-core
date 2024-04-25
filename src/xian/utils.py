import binascii
import json
import struct
import toml
import nacl
import nacl.encoding
import nacl.signing
import hashlib

import xian.constants as c

from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.stdlib.bridge.time import Datetime
from contracting.storage.encoder import encode, decode
from xian.exceptions import TransactionException
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
        raise TransactionException("Remove timestamp from metadata")

    chain_id = tx["payload"].get("chain_id", "")
    if not chain_id:
        raise TransactionException("Add chain_id to payload")

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
