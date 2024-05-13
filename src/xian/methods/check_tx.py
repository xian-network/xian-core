from cometbft.abci.v1beta3.types_pb2 import ResponseCheckTx
from xian.utils import (
    decode_transaction_bytes,
    unpack_transaction,
    verify,
    validate_transaction
)
from xian.constants import ErrorCode, OkCode

import json


def check_tx(self, raw_tx) -> ResponseCheckTx:
    try:
        tx = decode_transaction_bytes(raw_tx)
        validate_transaction(self.client,self.nonce_storage,tx)
        sender, signature, payload = unpack_transaction(tx)
        if not verify(sender, payload, signature):
            return ResponseCheckTx(code=ErrorCode, log="Bad signature")
        payload_json = json.loads(payload)
        if payload_json["chain_id"] != self.chain_id:
            return ResponseCheckTx(code=ErrorCode, log="Wrong chain_id")
        return ResponseCheckTx(code=OkCode)
    except Exception as e:
        return ResponseCheckTx(code=ErrorCode, log=f"{type(e).__name__}: {e}")
