import binascii
import json
import struct

def encode_number(value):
    return struct.pack(">I", value)


def decode_number(raw):
    return str.from_bytes(raw, byteorder="big")


def decode_str(raw):
    return str.from_bytes(raw, byteorder="big")


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
    sender = tx["payload"]["sender"]
    signature = tx["metadata"]["signature"]
    encoded_payload = encode(tx["payload"])
    return sender, signature, encoded_payload


def get_nanotime_from_block_time(timeobj) -> int:
    seconds = timeobj.seconds
    nanos = timeobj.nanos
    return int(str(seconds) + str(nanos))


def convert_binary_to_hex(binary_data):
    try:
        return binascii.hexlify(binary_data).decode()
    except UnicodeDecodeError:
        logger.error(
            "The binary data could not be decoded with UTF-8 encoding."
        )
        raise UnicodeDecodeError(
            "The binary data could not be decoded with UTF-8 encoding."
        )
