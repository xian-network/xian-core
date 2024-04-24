from cometbft.abci.v1beta1.types_pb2 import ResponseEcho


def echo(self, req) -> ResponseEcho:
    r = ResponseEcho()
    r.echo = req.message
    return r
