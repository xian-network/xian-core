import binascii
import json
import struct
from contracting.db.encoder import encode, decode
import os
import shutil
import logging
from contracting.stdlib.bridge.decimal import ContractingDecimal
import toml

from contracting.stdlib.bridge.time import Datetime

# Z85CHARS is the base 85 symbol table
Z85CHARS = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#"
# Z85MAP maps integers in [0,84] to the appropriate character in Z85CHARS
Z85MAP = {c: idx for idx, c in enumerate(Z85CHARS)}

_85s = [85**i for i in range(5)][::-1]

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


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
    return int(str(seconds) + str(nanos))


def convert_binary_to_hex(binary_data):
    try:
        return binascii.hexlify(binary_data).decode()
    except UnicodeDecodeError:
        logger.error("The binary data could not be decoded with UTF-8 encoding.")
        raise UnicodeDecodeError(
            "The binary data could not be decoded with UTF-8 encoding."
        )


def load_tendermint_config():
    config_path = os.getenv("CONFIG_PATH")
    path = os.path.dirname(os.path.abspath(__file__))
    toml_path = os.path.join(path, "config/config.toml" if not config_path else config_path)
    home = os.path.expanduser("~")
    if not os.path.exists(os.path.join(home, ".tendermint/")):
        logging.error("You must initialize tendermint before running this command.")

    tendermint_config_path = os.path.join(home, ".tendermint/config/config.toml")
    shutil.copyfile(toml_path, tendermint_config_path)
    logger.info("Copied config.toml to ~/.tendermint/config/config.toml")
    with open(tendermint_config_path, "r") as f:
        config = toml.load(tendermint_config_path)
    return config


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
    except Exception as e:
        return ""
    

def get_genesis_json():
    home = os.path.expanduser("~")
    path = os.path.join(home, ".tendermint/config/genesis.json")
    with open(path, "r") as f:
        genesis = json.load(f)
    return genesis
