from cometbft.abci.v1beta3.types_pb2 import ResponseCheckTx
from xian.utils import (
    decode_transaction_bytes,
    unpack_transaction,
)
import json

def check_tx(self, raw_tx) -> ResponseCheckTx:
    try:
        tx = decode_transaction_bytes(raw_tx)
        self.xian.validate_transaction(tx)
        sender, signature, payload = unpack_transaction(tx)
        if not verify(sender, payload, signature):
            return ResponseCheckTx(code=ErrorCode)
        payload_json = json.loads(payload)
        if payload_json["chain_id"] != self.chain_id:
            return ResponseCheckTx(code=ErrorCode)
        return ResponseCheckTx(code=OkCode)
    except Exception as e:
        return ResponseCheckTx(code=ErrorCode, info=f"ERROR: {e}")