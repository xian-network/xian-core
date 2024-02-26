from io import BytesIO

from abci.utils import write_message, read_messages

from tendermint.abci.types_pb2 import (
    Request,
    RequestDeliverTx,
    RequestEcho,
    RequestInfo,
)


def test_raw_decoding():
    from io import BytesIO

    # info + flush request
    # Note this is TM version specific!
    inbound = b"\x1e\x1a\r\n\x070.34.24\x10\x0b\x18\x08\x04\x12\x00"
    data = BytesIO(inbound)

    req_type = next(read_messages(data, Request))
    assert "info" == req_type.WhichOneof("value")

    req_type2 = next(read_messages(data, Request))
    assert "flush" == req_type2.WhichOneof("value")

    assert data.read() == b""


def test_encoding_decoding():
    echo = Request(echo=RequestEcho(message="hello"))
    raw = write_message(echo)
    buffer = BytesIO(raw)
    req = next(read_messages(buffer, Request))
    assert "echo" == req.WhichOneof("value")

    info = Request(info=RequestInfo(version="18.0"))
    raw1 = write_message(info)
    buffer1 = BytesIO(raw1)
    req = next(read_messages(buffer1, Request))
    assert "info" == req.WhichOneof("value")


def test_check_reading_batch():
    bits = b""
    for i in range(20):
        tx = (i).to_bytes(2, byteorder="big")
        bits += write_message(RequestDeliverTx(tx=tx))

    result = [m.tx for m in read_messages(BytesIO(bits), RequestDeliverTx)]
    assert len(result) == 20
