"""
TCP Server that communicates with Tendermint
"""
import asyncio
import signal
import platform
import io
import os

from .utils import *
from io import BytesIO
from loguru import logger
from cometbft.abci.v1beta3.types_pb2 import (
    Request,
    Response,
)
from cometbft.abci.v1beta1.types_pb2 import (
    ResponseFlush,
    ResponseException,
)

MaxReadInBytes = 64 * 1024  # Max we'll consume on a read stream


class ProtocolHandler:
    """
    Internal handler called by the server to process requests from
    Tendermint.  The handler delegates calls to your application
    """

    def __init__(self, app):
        self.app = app

    async def process(self, req_type: str, req) -> bytes:
        handler = getattr(self, req_type, self.no_match)
        if asyncio.iscoroutinefunction(handler):
            return await handler(req)
        else:
            return handler(req)

    def flush(self, req) -> bytes:
        response = Response(flush=ResponseFlush())
        return write_message(response)
    
    async def echo(self, req) -> bytes:
        result = await self.app.echo(req.echo)
        response = Response(echo=result)
        return write_message(response)

    async def info(self, req) -> bytes:
        result = await self.app.info(req.info)
        response = Response(info=result)
        return write_message(response)

    async def check_tx(self, req) -> bytes:
        result = await self.app.check_tx(req.check_tx.tx)
        response = Response(check_tx=result)
        return write_message(response)

    async def query(self, req) -> bytes:
        result = await self.app.query(req.query)
        response = Response(query=result)
        return write_message(response)

    async def commit(self, req) -> bytes:
        result = await self.app.commit()
        response = Response(commit=result)
        return write_message(response)
    
    async def finalize_block(self, req) -> bytes:
        result = await self.app.finalize_block(req.finalize_block)
        response = Response(finalize_block=result)
        return write_message(response)

    async def init_chain(self, req) -> bytes:
        result = await self.app.init_chain(req.init_chain)
        response = Response(init_chain=result)
        return write_message(response)

    async def list_snapshots(self, req) -> bytes:
        result = await self.app.list_snapshots(req.list_snapshots)
        response = Response(list_snapshots=result)
        return write_message(response)

    async def offer_snapshot(self, req) -> bytes:
        result = await self.app.offer_snapshot(req.offer_snapshot)
        response = Response(offer_snapshot=result)
        return write_message(response)

    async def load_snapshot_chunk(self, req) -> bytes:
        result = await self.app.load_snapshot_chunk(req.load_snapshot_chunk)
        response = Response(load_snapshot_chunk=result)
        return write_message(response)

    async def apply_snapshot_chunk(self, req) -> bytes:
        result = await self.app.apply_snapshot_chunk(req.apply_snapshot_chunk)
        response = Response(apply_snapshot_chunk=result)
        return write_message(response)
    
    async def process_proposal(self, req) -> bytes:
        result = await self.app.process_proposal(req.process_proposal)
        response = Response(process_proposal=result)
        return write_message(response)
    
    async def prepare_proposal(self, req) -> bytes:
        result = await self.app.prepare_proposal(req.prepare_proposal)
        response = Response(prepare_proposal=result)
        return write_message(response)

    async def no_match(self, req) -> bytes:
        response = Response(
            exception=ResponseException(error="ABCI request not found")
        )
        return write_message(response)


class ABCIServer:
    """
    Async TCP server
    """

    protocol: ProtocolHandler
    
    def __init__(self, app, socket_path="/tmp/abci.sock") -> None:
        """
        Requires App and an optional port if you changed the ABCI port on
        Tendermint
        """
        self.socket_path = socket_path
        self.protocol = ProtocolHandler(app)

    def run(self) -> None:
        """
        Run the application
        """
        # Check OS to handle signals appropriately
        on_windows = platform.system() == "Windows"

        loop = asyncio.get_event_loop()
        if not on_windows:
            # Unix...register signal handlers
            loop.add_signal_handler(
                signal.SIGINT, lambda: asyncio.create_task(_stop())
            )
            loop.add_signal_handler(
                signal.SIGTERM, lambda: asyncio.create_task(_stop())
            )
        try:
            logger.info(" ~ running app - press CTRL-C to stop ~")
            loop.run_until_complete(self._start())
        except asyncio.exceptions.CancelledError:
            pass
        except Exception as e:
            logger.error(f" ... error: {e}")
            logger.warning(" ... shutting down")
            if on_windows:
                loop.run_until_complete(_stop())
        finally:
            loop.stop()

    async def _start(self) -> None:
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        self.server = await asyncio.start_unix_server(
            self._handler,
            path=self.socket_path,
        )
        await self.server.serve_forever()

    async def _handler(
            self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        data = BytesIO()
        while True:
            # Read data from the reader
            bits = await reader.read(MaxReadInBytes)
            if len(bits) == 0:
                logger.error(" ... tendermint closed connection")
                break  # Exit the loop if the connection is closed

            # Append new data to the buffer
            data.seek(0, io.SEEK_END)
            data.write(bits)
            data.seek(0)  # Reset position to start of buffer

            # Attempt to parse and process messages
            while True:
                start_pos = data.tell()
                messages = list(read_messages(data, Request))
                if not messages:
                    # No complete messages available, reset position and wait
                    data.seek(start_pos)
                    break  # Exit the parsing loop to read more data

                for message in messages:
                    req_type = message.WhichOneof("value")
                    response = await self.protocol.process(req_type, message)
                    writer.write(response)
                    await writer.drain()
                    # Update start position after processing
                    start_pos = data.tell()

            # Remove processed data from the buffer
            remaining_data = data.read()
            data = BytesIO()
            data.write(remaining_data)
            data.seek(0)  # Reset position to start of buffer

        # Shut down if the connection is closed
        await _stop()


async def _stop() -> None:
    """
    Clean up all async tasks.
    Called on a signal or a connection closed by tendermint
    """
    logger.warning(" ... received exit signal")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)