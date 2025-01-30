import secrets
import socket
import pathlib
import json
import struct

from loguru import logger
from datetime import datetime
from contracting.execution.executor import Executor
from contracting.stdlib.bridge.time import Datetime
from contracting.storage.encoder import safe_repr, convert_dict
from contracting.storage.driver import Driver
from xian.utils.tx import format_dictionary
from xian.utils.encoding import stringify_decimals
from xian.constants import Constants as c


class Simulator:
    def __init__(self):
        simulator_socket = pathlib.Path(c.SIMULATOR_SOCKET)
        logger.debug(f"Using socket file: {simulator_socket}")

        # If the socket file exists, remove it
        if simulator_socket.exists():
            simulator_socket.unlink()

        # Create a socket
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(c.SIMULATOR_SOCKET)
        self.socket.listen(1)

    def listen(self):
        logger.debug("Listening...")

        while True:
            connection, client_address = self.socket.accept()
            logger.debug("Client connected")

            try:
                while True:
                    try:
                        # Read message length (4 bytes)
                        raw_msglen = connection.recv(4)
                        if not raw_msglen:
                            break
                        if len(raw_msglen) < 4:
                            # Handle incomplete length prefix
                            raise ValueError("Incomplete length prefix received")
                        msglen = struct.unpack('>I', raw_msglen)[0]

                        # Read the message data
                        data = b''

                        while len(data) < msglen:
                            packet = connection.recv(msglen - len(data))
                            if not packet:
                                # No more data from client, client closed connection
                                logger.debug(f"Client disconnected")
                                break
                            data += packet

                        if not data:
                            logger.debug(f"Client disconnected")
                            break

                        # Parse the JSON payload directly from bytes
                        payload = json.loads(data)
                        logger.debug(f"Received payload: {payload}")

                        try:
                            response = self.execute(payload)
                            response = json.dumps(response)
                            response = response.encode()
                            message_length = struct.pack('>I', len(response))
                            connection.sendall(message_length + response)
                        except BrokenPipeError:
                            logger.error(f"Cannot send data, broken pipe.")
                            break
                    except ConnectionResetError:
                        logger.debug(f"Client disconnected")
                        break
            finally:
                logger.debug(f"Client disconnected")
                connection.close()

    def generate_environment(self, num=1):
        random_hex_string = secrets.token_hex(nbytes=64 // 2)

        env_json = {
            'block_hash': random_hex_string,
            'block_num': num,
            '__input_hash': random_hex_string,
            'now': Datetime._from_datetime(datetime.now()),
            'AUXILIARY_SALT': random_hex_string
        }

        return env_json

    def execute_tx(self, payload, stamp_cost, environment: dict = {}, executor=None):

        balance = 9999999
        output = executor.execute(
            sender=payload['sender'],
            contract_name=payload['contract'],
            function_name=payload['function'],
            stamps=balance * stamp_cost,
            stamp_cost=stamp_cost,
            kwargs=convert_dict(payload['kwargs']),
            environment=environment,
            auto_commit=False,
            metering=True
        )

        executor.driver.flush_cache()

        writes = [{'key': k, 'value': v} for k, v in output['writes'].items()]

        tx_output = {
            'payload': payload,
            'status': output['status_code'],
            'state': writes,
            'stamps_used': output['stamps_used'],
            'result': safe_repr(output['result'])
        }

        tx_output = stringify_decimals(format_dictionary(tx_output))
        logger.debug(f'Result: {tx_output}')

        return tx_output

    def execute(self, payload):
        driver = Driver(storage_home=c.STORAGE_HOME)
        executor = Executor(metering=False, bypass_balance_amount=True, bypass_cache=True, driver=driver)
        environment = self.generate_environment()
        try:
            stamp_cost = int(executor.driver.get_var(contract='stamp_cost', variable='S', arguments=['value']))
        except:
            stamp_cost = 20
        return self.execute_tx(
            payload=payload,
            environment=environment,
            stamp_cost=stamp_cost,
            executor=executor
        )


if __name__ == '__main__':
    Simulator().listen()
