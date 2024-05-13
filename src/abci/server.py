"""
TCP Server that communicates with Tendermint
"""
import asyncio
import signal
import platform
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

DefaultABCIPort = 26658
MaxReadInBytes = 64 * 1024  # Max we'll consume on a read stream


class ProtocolHandler:
    """
    Internal handler called by the server to process requests from
    Tendermint.  The handler delegates calls to your application
    """

    def __init__(self, app):
        self.app = app

    def process(self, req_type: str, req) -> bytes:
        handler = getattr(self, req_type, self.no_match)
        return handler(req)

    def flush(self, req) -> bytes:
        response = Response(flush=ResponseFlush())
        return write_message(response)
    
    def echo(self, req) -> bytes:
        result = self.app.echo(req.echo)
        response = Response(echo=result)
        return write_message(response)

    def info(self, req) -> bytes:
        result = self.app.info(req.info)
        response = Response(info=result)
        return write_message(response)

    def check_tx(self, req) -> bytes:
        result = self.app.check_tx(req.check_tx.tx)
        response = Response(check_tx=result)
        return write_message(response)

    def query(self, req) -> bytes:
        result = self.app.query(req.query)
        response = Response(query=result)
        return write_message(response)

    def commit(self, req) -> bytes:
        result = self.app.commit()
        response = Response(commit=result)
        return write_message(response)
    
    def finalize_block(self, req) -> bytes:
        result = self.app.finalize_block(req.finalize_block)
        response = Response(finalize_block=result)
        return write_message(response)

    def init_chain(self, req) -> bytes:
        result = self.app.init_chain(req.init_chain)
        response = Response(init_chain=result)
        return write_message(response)

    def list_snapshots(self, req) -> bytes:
        result = self.app.list_snapshots(req.list_snapshots)
        response = Response(list_snapshots=result)
        return write_message(response)

    def offer_snapshot(self, req) -> bytes:
        result = self.app.offer_snapshot(req.offer_snapshot)
        response = Response(offer_snapshot=result)
        return write_message(response)

    def load_snapshot_chunk(self, req) -> bytes:
        result = self.app.load_snapshot_chunk(req.load_snapshot_chunk)
        response = Response(load_snapshot_chunk=result)
        return write_message(response)

    def apply_snapshot_chunk(self, req) -> bytes:
        result = self.app.apply_snapshot_chunk(req.apply_snapshot_chunk)
        response = Response(apply_snapshot_chunk=result)
        return write_message(response)
    
    def process_proposal(self, req) -> bytes:
        result = self.app.process_proposal(req.process_proposal)
        response = Response(process_proposal=result)
        return write_message(response)
    
    def prepare_proposal(self, req) -> bytes:
        result = self.app.prepare_proposal(req.prepare_proposal)
        response = Response(prepare_proposal=result)
        return write_message(response)

    def no_match(self, req) -> bytes:
        response = Response(
            exception=ResponseException(error="ABCI request not found")
        )
        return write_message(response)


class ABCIServer:
    """
    Async TCP server
    """

    port: int
    protocol: ProtocolHandler
    
    def __init__(self, app, port=DefaultABCIPort) -> None:
        """
        Requires App and an optional port if you changed the ABCI port on
        Tendermint
        """
        self.port = port
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
        except:
            logger.warning(" ... shutting down")
            if on_windows:
                loop.run_until_complete(_stop())
        finally:
            loop.stop()

    async def _start(self) -> None:
        self.server = await asyncio.start_server(
            self._handler,
            host="0.0.0.0",
            port=self.port,
        )
        await self.server.serve_forever()

    async def _handler(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        ip, socket, *_ = writer.get_extra_info("peername")
        logger.info(f" ... connection @ {ip}:{socket}")

        data = BytesIO()
        last_pos = 0

        while True:
            if last_pos == data.tell():
                data = BytesIO()
                last_pos = 0
            
            bits = await reader.read(MaxReadInBytes)
            if len(bits) == 0:
                logger.error(" ... tendermint closed connection")
                # break to the _stop if the connection stops
                break

            data.write(bits)
            data.seek(last_pos)

            ## Tendermint prefixes each serialized protobuf message
            ## with varint encoded length. We use the 'data' buffer to
            ## keep track of where we are in the byte stream and progress
            ## based on the length encoding
            for message in read_messages(data, Request):
                req_type = message.WhichOneof("value")
                response = self.protocol.process(req_type, message)
                writer.write(response)
                last_pos = data.tell()

        # Any connection fails and we shut the whole thing down
        await _stop()


async def _stop() -> None:
    """
    Clean up all async tasks.  Called on a signal or a connection closed by
    tendermint
    """
    logger.warning(" ... received exit signal")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
