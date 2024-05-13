import json

from cometbft.abci.v1beta1.types_pb2 import ResponseQuery
from xian.utils import encode_str
from xian.constants import (
    OkCode,
    ErrorCode
)
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.compilation import parser
from contracting.storage.encoder import Encoder
from loguru import logger


def query(self, req) -> ResponseQuery:
    """
    Query the application state
    Request Ex. http://localhost:26657/abci_query?path="path"
    (Yes you need to quote the path)
    """

    result = None
    key = ""

    try:
        request_path = req.path
        path_parts = [part for part in request_path.split("/") if part]

        # http://localhost:26657/abci_query?path="/get/currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"
        if path_parts and path_parts[0] == "get":
            result = self.client.raw_driver.get(path_parts[1])
            key = path_parts[1]

        # http://localhost:26657/abci_query?path="/keys/currency.balances" BLOCK SERVICE MODE ONLY
        if self.block_service_mode:
            if path_parts[0] == "keys":
                result = self.client.raw_driver.get(path_parts[1])
            if path_parts[0] == "contracts":
                result = self.client.raw_driver.get_contract_files()

        # http://localhost:26657/abci_query?path="/estimate_stamps/<encoded_txn>" BLOCK SERVICE MODE ONLY
        if self.block_service_mode:
            if path_parts[0] == "estimate_stamps":
                raw_tx = path_parts[1]
                byte_data = bytes.fromhex(raw_tx)
                tx_hex = byte_data.decode("utf-8")
                tx = json.loads(tx_hex)
                result = self.stamp_estimator.execute(tx)

        # http://localhost:26657/abci_query?path="/health"
        if path_parts[0] == "health":
            result = "OK"

        # http://localhost:26657/abci_query?path="/get_next_nonce/ddd326fddb5d1677595311f298b744a4e9f415b577ac179a6afbf38483dc0791"
        if path_parts[0] == "get_next_nonce":
            result = self.nonce_storage.get_next_nonce(sender=path_parts[1])

        # http://localhost:26657/abci_query?path="/contract/con_some_contract"
        if path_parts[0] == "contract":
            result = self.client.raw_driver.get_contract(path_parts[1])

        # http://localhost:26657/abci_query?path="/contract_methods/con_some_contract"
        if path_parts[0] == "contract_methods":
            contract_code = self.client.raw_driver.get_contract(path_parts[1])
            if contract_code is not None:
                funcs = parser.methods_for_contract(contract_code)
                result = {"methods": funcs}

        # http://localhost:26657/abci_query?path="/contract_vars/con_some_contract"
        if path_parts[0] == "contract_vars":
            contract_code = self.client.raw_driver.get_contract(path_parts[1])
            if contract_code is not None:
                result = parser.variables_for_contract(contract_code)

        # http://localhost:26657/abci_query?path="/ping"
        if path_parts[0] == "ping":
            result = {'status': 'online'}

        if result:
            if isinstance(result, str):
                v = encode_str(result)
                type_of_data = "str"
            elif isinstance(result, int):
                v = encode_str(str(result))
                type_of_data = "int"
            elif isinstance(result, float) or isinstance(result, ContractingDecimal):
                v = encode_str(str(result))
                type_of_data = "decimal"
            elif isinstance(result, dict) or isinstance(result, list):
                v = encode_str(json.dumps(result, cls=Encoder))
                type_of_data = "str"
            else:
                v = encode_str(str(result))
                type_of_data = "str"
        else:
            # If no result, return a byte string representing None
            v = b"\x00"
            type_of_data = "None"

    except Exception as e:
        logger.error(f"QUERY ERROR: {e}")
        return ResponseQuery(code=ErrorCode, log=f"QUERY ERROR")

    return ResponseQuery(code=OkCode, value=v, info=type_of_data, key=encode_str(key))
