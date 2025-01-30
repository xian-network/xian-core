import json
import binascii
import hashlib
import decimal

from typing import Tuple
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.stdlib.bridge.time import Datetime
from loguru import logger


def encode_str(value):
    return value.encode("utf-8")


def decode_transaction_bytes(raw) -> Tuple[dict, str]:
    tx_bytes = raw
    tx_hex = tx_bytes.decode("utf-8")
    tx_decoded_bytes = bytes.fromhex(tx_hex)
    tx_str = tx_decoded_bytes.decode("utf-8")
    tx_json = json.loads(tx_str)
    payload_str = extract_payload_string(tx_str)

    assert json.loads(payload_str) == tx_json["payload"], 'Invalid payload'
    return tx_json, payload_str


def encode_transaction_bytes(tx_str: str) -> bytes:
    tx_bytes = tx_str.encode("utf-8")
    tx_hex = binascii.hexlify(tx_bytes).decode("utf-8")
    return tx_hex.encode("utf-8")


def extract_payload_string(json_str):
    try:
        # Find the start of the 'payload' object
        start_index = json_str.find('"payload":')
        if start_index == -1:
            raise ValueError("No 'payload' found in the provided JSON string.")
        
        # Find the opening brace of the 'payload' object
        start_brace_index = json_str.find('{', start_index)
        if start_brace_index == -1:
            raise ValueError("Malformed JSON: No opening brace for 'payload'.")

        # Use a stack to find the matching closing brace, ignoring braces within strings
        brace_count = 0
        in_string = False
        i = start_brace_index
        while i < len(json_str):
            char = json_str[i]
            
            if char == '"' and (i == 0 or json_str[i-1] != '\\'):
                in_string = not in_string
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
            
            # When brace_count is zero, we've found the matching closing brace
            if brace_count == 0:
                return json_str[start_brace_index:i+1]
            
            i += 1
        
        raise ValueError("Malformed JSON: No matching closing brace for 'payload'.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise

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
    try:
        if isinstance(obj, ContractingDecimal):
            return str(obj)
        elif isinstance(obj, decimal.Decimal):
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

