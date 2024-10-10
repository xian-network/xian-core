import json
import binascii
import hashlib
from contracting.stdlib.bridge.time import Datetime
from loguru import logger

def encode_str(value):
    return value.encode("utf-8")

def decode_transaction_bytes(raw):
    tx_bytes = raw
    tx_hex = tx_bytes.decode("utf-8")
    tx_decoded_bytes = bytes.fromhex(tx_hex)
    tx_str = tx_decoded_bytes.decode("utf-8")
    tx_json = json.loads(tx_str)
    return tx_json

def hash_bytes(bytes_data):
    return hashlib.sha256(bytes_data).hexdigest()

def convert_binary_to_hex(binary_data):
    try:
        return binascii.hexlify(binary_data).decode()
    except UnicodeDecodeError as e:
        logger.error(f"The binary data could not be decoded with UTF-8 encoding: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise

def convert_special_types(obj):
    try:
        if isinstance(obj, Datetime):
            return obj.isoformat()
        elif isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return str(obj)
        elif isinstance(obj, float):
            # Optionally raise an error if floats are not allowed
            raise TypeError("Float values are not allowed due to precision loss. Use integers or strings.")
        elif isinstance(obj, dict):
            return {key: convert_special_types(val) for key, val in obj.items()}
        elif isinstance(obj, list):
            return [convert_special_types(elem) for elem in obj]
        else:
            return obj
    except Exception as e:
        logger.error(f"Error in convert_special_types: {e}")
        return ""
