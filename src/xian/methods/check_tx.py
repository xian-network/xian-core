from cometbft.abci.v1beta3.types_pb2 import ResponseCheckTx
from xian.utils.tx import (
    validate_transaction
)
from xian.utils.tx import (
    verify,
    unpack_transaction
)
from xian.utils.encoding import decode_transaction_bytes
from xian.constants import Constants as c

import json


async def check_tx(self, raw_tx) -> ResponseCheckTx:
    try:
        tx, payload_str = decode_transaction_bytes(raw_tx)
        validate_transaction(self.client,self.nonce_storage,tx)
        sender, signature, payload = unpack_transaction(tx)
        if not verify(sender, payload_str, signature):
            return ResponseCheckTx(code=c.ErrorCode, log="Bad signature")
        payload_json = json.loads(payload)
        if payload_json["chain_id"] != self.chain_id:
            return ResponseCheckTx(code=c.ErrorCode, log="Wrong chain_id")
        return ResponseCheckTx(code=c.OkCode)
    except Exception as e:
        return ResponseCheckTx(code=c.ErrorCode, log=f"{type(e).__name__}: {e}")
