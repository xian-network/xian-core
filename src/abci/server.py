import asyncio
import signal
import platform
import os

from loguru import logger
from dataclasses import dataclass
from cometbft.abci.v1beta3.types_pb2 import Request, Response
from cometbft.abci.v1beta1.types_pb2 import ResponseFlush, ResponseException
from .utils import read_messages, write_message
from io import BytesIO

# Max we'll consume on a read stream
MaxReadInBytes = 64 * 1024


@dataclass
class ProtocolHandler:
    app: object

    def process(self, req_type: str, req) -> bytes:
        handler = getattr(self, req_type, self.no_match)
        return handler(req)

    def create_response(self, response_type, result=None) -> bytes:
        response = Response(**{response_type: result})
        return write_message(response)

    def flush(self, req) -> bytes:
        return self.create_response(
            'flush',
            ResponseFlush()
        )
    
    def echo(self, req) -> bytes:
        return self.create_response(
            'echo',
            self.app.echo(req.echo)
        )

    def info(self, req) -> bytes:
        return self.create_response(
            'info',
            self.app.info(req.info)
        )

    def check_tx(self, req) -> bytes:
        return self.create_response(
            'check_tx',
            self.app.check_tx(req.check_tx.tx)
        )

    def query(self, req) -> bytes:
        return self.create_response(
            'query',
            self.app.query(req.query)
        )

    def commit(self, req) -> bytes:
        return self.create_response(
            'commit',
            self.app.commit()
        )
    
    def finalize_block(self, req) -> bytes:
        return self.create_response(
            'finalize_block',
            self.app.finalize_block(req.finalize_block)
        )

    def init_chain(self, req) -> bytes:
        return self.create_response(
            'init_chain',
            self.app.init_chain(req.init_chain)
        )

    def list_snapshots(self, req) -> bytes:
        return self.create_response(
            'list_snapshots',
            self.app.list_snapshots(req.list_snapshots)
        )

    def offer_snapshot(self, req) -> bytes:
        return self.create_response(
            'offer_snapshot',
            self.app.offer_snapshot(req.offer_snapshot)
        )

    def load_snapshot_chunk(self, req) -> bytes:
        return self.create_response(
            'load_snapshot_chunk',
            self.app.load_snapshot_chunk(req.load_snapshot_chunk)
        )

    def apply_snapshot_chunk(self, req) -> bytes:
        return self.create_response(
            'apply_snapshot_chunk',
            self.app.apply_snapshot_chunk(req.apply_snapshot_chunk)
        )
    
    def process_proposal(self, req) -> bytes:
        return self.create_response(
            'process_proposal',
            self.app.process_proposal(req.process_proposal)
        )
    
    def prepare_proposal(self, req) -> bytes:
        return self.create_response(
            'prepare_proposal',
            self.app.prepare_proposal(req.prepare_proposal)
        )

    def no_match(self, req) -> bytes:
        return self.create_response(
            'exception',
            ResponseException(error="ABCI request not found")
        )


class ABCIServer:
    def __init__(self, app, socket_path="/tmp/abci.sock") -> None:
        self.socket_path = socket_path
        self.protocol = ProtocolHandler(app)
        self._stop_event = asyncio.Event()
        self._server = None

    def run(self) -> None:
        loop = asyncio.get_event_loop()
        if platform.system() != "Windows":
            loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self.stop()))
            loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.stop()))

        try:
            logger.info(" ~ running app - press CTRL-C to stop ~")
            loop.run_until_complete(self._start())
        except Exception as e:
            logger.warning(f" ... shutting down due to: {e}")
            loop.run_until_complete(self.stop())
        finally:
            pending = asyncio.all_tasks(loop)
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    async def _start(self) -> None:
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        
        self._server = await asyncio.start_unix_server(
            self._handler,
            path=self.socket_path,
        )
        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            logger.info(" ... _start task cancelled")
        finally:
            os.remove(self.socket_path)

    async def _handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        buffer = bytearray()
        
        try:
            while True:
                data = await reader.read(MaxReadInBytes)
                if not data:
                    logger.error(" ... tendermint closed connection")
                    break

                buffer.extend(data)

                responses = []
                while True:
                    message, remaining_data = self._parse_message(buffer)
                    if message is None:
                        break
                    
                    req_type = message.WhichOneof("value")
                    response = self.protocol.process(req_type, message)
                    responses.append(response)
                    
                    buffer = bytearray(remaining_data)

                if responses:
                    writer.writelines(responses)
                    await writer.drain()
        except asyncio.CancelledError:
            logger.info(" ... handler task cancelled")
        except Exception as e:
            logger.error(f" ... handler exception: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    def _parse_message(self, buffer: bytearray):
        try:
            data = BytesIO(buffer)
            message = next(read_messages(data, Request))
            remaining_data = data.read()
            return message, remaining_data
        except StopIteration:
            return None, buffer

    async def stop(self) -> None:
        logger.warning(" ... received exit signal")
        self._stop_event.set()

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        logger.info(f" ... cancelling {len(tasks)} tasks")
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(" ... all tasks cancelled")
