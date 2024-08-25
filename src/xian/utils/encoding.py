import json
import binascii
import hashlib
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.stdlib.bridge.time import Datetime


def encode_str(value):
    return value.encode("utf-8")


def decode_transaction_bytes(raw):
    tx_bytes = raw
    tx_hex = tx_bytes.decode("utf-8")
    tx_decoded_bytes = bytes.fromhex(tx_hex)
    tx_str = tx_decoded_bytes.decode("utf-8")
    tx_json = json.loads(tx_str)
    return tx_json


def hash_bytes(bytes):
    return hashlib.sha256(bytes).hexdigest()


def convert_binary_to_hex(binary_data):
    try:
        return binascii.hexlify(binary_data).decode()
    except UnicodeDecodeError as e:
        logger.error(f"The binary data could not be decoded with UTF-8 encoding: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise


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