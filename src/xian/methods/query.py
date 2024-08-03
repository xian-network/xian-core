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

    logger.debug(req.path)
    path_parts = [part for part in req.path.split("/") if part]
    loop = asyncio.get_event_loop()
    key = path_parts[1]
    result = None

    try:
        # http://localhost:26657/abci_query?path="/get/currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"
        if path_parts and path_parts[0] == "get":
            result = await loop.run_in_executor(None, self.client.raw_driver.get, path_parts[1])

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

        # Blockchain Data Service
        if self.block_service_mode:
            limit = 100
            offset = 0

            params = dict()
            for path in path_parts:
                if '=' in path:
                    param_list = path.split('=')
                    params[param_list[0]] = param_list[1]

            if 'limit' in params and int(params['limit']) < limit:
                limit = int(params['limit'])
            if 'offset' in params:
                offset = int(params['offset'])

            # http://localhost:26657/abci_query?path="/state/currency.balances"
            elif path_parts[0] == "state":
                result = await self.bds.get_state(key)
                print('state', result)  # TODO: Remove

            # http://localhost:26657/abci_query?path="/state_history/currency.balances:ee06a34cf08bf72ce592d26d36b90c79daba2829ba9634992d034318160d49f9/limit=10/offset=20"
            if path_parts[0] == "state_history":
                result = await self.bds.get_state_history(key, limit, offset)
                print('state_history', result)  # TODO: Remove

            # http://localhost:26657/abci_query?path="/state_for_tx/f39b4ea880088cfae45538acb2f7fdae1e70112185a5523d1027bcf74eac3919"
            elif path_parts[0] == "state_for_tx":
                result = await self.bds.get_state_for_tx(key)
                print('state_for_tx', result)  # TODO: Remove

            # Block Height: http://localhost:26657/abci_query?path="/state_for_block/662"
            # Block Hash: http://localhost:26657/abci_query?path="/state_for_block/34F1A1C923D23C5C0531490E714FC56F501EDADF05B6BF68C2ED3923234E0CC4"
            elif path_parts[0] == "state_for_block":
                result = await self.bds.get_state_for_block(key)
                print('state_for_block', result)  # TODO: Remove

            # http://localhost:26657/abci_query?path="/contracts/limit=10/offset=20"
            elif path_parts[0] == "contracts":
                result = await self.bds.get_contracts(limit, offset)
                print('contracts', result)  # TODO: Remove

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

            # http://localhost:26657/abci_query?path="/calculate_stamps/<encoded_tx>"
            elif path_parts[0] == "calculate_stamps":
                raw_tx = path_parts[1]
                byte_data = bytes.fromhex(raw_tx)
                tx_hex = byte_data.decode("utf-8")
                tx = json.loads(tx_hex)
                result = await loop.run_in_executor(None, self.stamp_calculator.execute, tx)

        else:
            error = f'Unknown query path: {path_parts[0]}'
            logger.error(error)
            return ResponseQuery(code=ErrorCode, value=b"\x00", info=None, log=error)

        if result is None:
            v = None
            type_of_data = None
        elif isinstance(result, str):
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

    except Exception as err:
        logger.error(err)
        return ResponseQuery(code=ErrorCode, log=err)

    return ResponseQuery(code=OkCode, value=v, info=type_of_data, key=encode_str(key))
