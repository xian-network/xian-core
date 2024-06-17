import base64
import json
import ast
import re
import asyncio
from cometbft.abci.v1beta1.types_pb2 import ResponseQuery
from xian.utils import encode_str
from xian.constants import (
    OkCode,
    ErrorCode
)
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.compilation import parser
from contracting.compilation.linter import Linter
from contracting.storage.encoder import Encoder
from loguru import logger
from pyflakes.api import check
from pyflakes.reporter import Reporter
from urllib.parse import unquote
from io import StringIO


async def query(self, req) -> ResponseQuery:
    """
    Query the application state
    Request Ex. http://localhost:26657/abci_query?path="path"
    (Yes you need to quote the path)
    """

    loop = asyncio.get_event_loop()
    result = None
    key = ""

    try:
        logger.debug(req.path)
        request_path = req.path
        path_parts = [part for part in request_path.split("/") if part]

        # http://localhost:26657/abci_query?path="/get/currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"
        if path_parts and path_parts[0] == "get":
            result = await loop.run_in_executor(None, self.client.raw_driver.get, path_parts[1])
            key = path_parts[1]

        # http://localhost:26657/abci_query?path="/health"
        elif path_parts[0] == "health":
            result = "OK"

        # http://localhost:26657/abci_query?path="/get_next_nonce/ddd326fddb5d1677595311f298b744a4e9f415b577ac179a6afbf38483dc0791"
        elif path_parts[0] == "get_next_nonce":
            result = await loop.run_in_executor(None, self.nonce_storage.get_next_nonce, path_parts[1])

        # http://localhost:26657/abci_query?path="/contract/con_some_contract"
        elif path_parts[0] == "contract":
            result = await loop.run_in_executor(None, self.client.raw_driver.get_contract, path_parts[1])

        # http://localhost:26657/abci_query?path="/contract_methods/con_some_contract"
        elif path_parts[0] == "contract_methods":
            contract_code = await loop.run_in_executor(None, self.client.raw_driver.get_contract, path_parts[1])
            if contract_code is not None:
                funcs = parser.methods_for_contract(contract_code)
                result = {"methods": funcs}

        # http://localhost:26657/abci_query?path="/contract_vars/con_some_contract"
        elif path_parts[0] == "contract_vars":
            contract_code = await loop.run_in_executor(None, self.client.raw_driver.get_contract, path_parts[1])
            if contract_code is not None:
                result = parser.variables_for_contract(contract_code)

        # http://localhost:26657/abci_query?path="/ping"
        elif path_parts[0] == "ping":
            result = {'status': 'online'}

        # BLOCK SERVICE MODE
        if self.block_service_mode:
            # http://localhost:26657/abci_query?path="/keys/currency.balances"
            if path_parts[0] == "keys":
                list_of_keys = await loop.run_in_executor(None, self.client.raw_driver.keys, path_parts[1])
                result = [key.split(":")[1] for key in list_of_keys]
                key = path_parts[1]

            # http://localhost:26657/abci_query?path="/contracts"
            elif path_parts[0] == "contracts":
                result = await loop.run_in_executor(None, self.client.raw_driver.get_contract_files)

            # http://localhost:26657/abci_query?path="/lint/<code>"
            elif path_parts[0] == "lint":
                try:
                    code = base64.b64decode(path_parts[1]).decode("utf-8")
                    code = unquote(code)

                    # Pyflakes linting
                    stdout = StringIO()
                    stderr = StringIO()
                    reporter = Reporter(stdout, stderr)
                    await loop.run_in_executor(None, check, code, "<string>", reporter)
                    stdout_output = stdout.getvalue()
                    stderr_output = stderr.getvalue()

                    # Contracting linting
                    try:
                        linter = Linter()
                        tree = await loop.run_in_executor(None, ast.parse, code)
                        violations = await loop.run_in_executor(None, linter.check, tree)
                        formatted_new_linter_output = ""
                        # Transform new linter output to match pyflakes format
                        if violations:
                            for violation in violations:
                                line = int(re.search(r"Line (\d+):", violation).group(1))
                                message = re.search(r"Line \d+: (.+)", violation).group(1)
                                formatted_violation_output = f"<string>:{line}:0: {message}\n"
                                formatted_new_linter_output += formatted_violation_output
                    except:
                        formatted_new_linter_output = ""

                    # Combine stderr output
                    combined_stderr_output = f"{stderr_output}{formatted_new_linter_output}"

                    result = {"stdout": stdout_output, "stderr": combined_stderr_output}
                except:
                    result = {"stdout": "", "stderr": ""}

            # TODO: Deprecated - Remove after tooling adjusted to 'calculate_stamps' endpoint
            # http://localhost:26657/abci_query?path="/estimate_stamps/<encoded_tx>"
            elif path_parts[0] == "calculate_stamps" or path_parts[0] == "estimate_stamps":
                raw_tx = path_parts[1]
                byte_data = bytes.fromhex(raw_tx)
                tx_hex = byte_data.decode("utf-8")
                tx = json.loads(tx_hex)
                result = await loop.run_in_executor(None, self.stamp_calculator.execute, tx)

        if result is not None:
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
            error = f'Unknown query path: {path_parts[0]}'
            logger.error(error)
            return ResponseQuery(code=ErrorCode, value=b"\x00", info=None, log=error)

    except Exception as err:
        logger.error(err)
        return ResponseQuery(code=ErrorCode, log=err)

    return ResponseQuery(code=OkCode, value=v, info=type_of_data, key=encode_str(key))
