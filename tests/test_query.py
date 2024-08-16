import os
import unittest
from io import BytesIO
import logging

from xian.constants import Constants
from xian.xian_abci import Xian
from abci.server import ProtocolHandler
from abci.utils import read_messages
from fixtures.test_constants import TestConstants

from cometbft.abci.v1beta3.types_pb2 import (
    Request,
    Response,
)
from cometbft.abci.v1beta1.types_pb2 import (
    RequestQuery,
    ResponseQuery,
)
import json


# Disable any kind of logging
logging.disable(logging.CRITICAL)


async def deserialize(raw: bytes) -> Response:
    try:
        resp = next(read_messages(BytesIO(raw), Response))
        return resp
    except Exception as e:
        logging.error("Deserialization error: %s", e)
        raise

class TestInfo(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.app = await Xian.create(constants=TestConstants)
        self.app.current_block_meta = {"height": 0, "nanos": 0, "chain_id": "test_chain"}
        self.app.client.raw_driver.set_contract("currency", '''balances = Hash(default_value=0)

@construct
def seed(vk: str):
    balances[vk] = 5555555.55 # 5% Team Tokens
    balances["team_lock"] = 16666666.65 # 15% Team Tokens 5 Year Release, Directly minted into Lock contract
    balances["dao"] = 33333333.3 # 30% DAO Tokens, Directly minted into DAO contract
    balances[vk] += 49999999.95 # 45% Second batch of public tokens, to be sent out after mint
    balances[vk] += 5555555.55 # 5% First batch of public tokens, to be sent out after mint

@export
def transfer(amount: float, to: str):
    assert amount > 0, 'Cannot send negative balances!'

    sender = ctx.caller

    assert balances[sender] >= amount, 'Not enough coins to send!'

    balances[sender] -= amount
    balances[to] += amount

@export
def balance_of(account: str):
    return balances[account]

@export
def allowance(owner: str, spender: str):
    return balances[owner, spender]

@export
def approve(amount: float, to: str):
    assert amount > 0, 'Cannot send negative balances!'

    sender = ctx.caller
    balances[sender, to] += amount
    return balances[sender, to]

@export
def transfer_from(amount: float, to: str, main_account: str):
    assert amount > 0, 'Cannot send negative balances!'

    sender = ctx.caller

    assert balances[main_account, sender] >= amount, 'Not enough coins approved to send! You have {} and are trying to spend {}'\
        .format(balances[main_account, sender], amount)
    assert balances[main_account] >= amount, 'Not enough coins to send!'

    balances[main_account, sender] -= amount
    balances[main_account] -= amount

    balances[to] += amount
''')
        self.app.client.raw_driver.set("currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6", 123.45)
        self.handler = ProtocolHandler(self.app)

    async def process_request(self, request_type, req):
        raw = await self.handler.process(request_type, req)
        resp = await deserialize(raw)
        return resp

    async def test_get_query(self):
        request = Request(query=RequestQuery(path="/get/currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"))
        response = await self.process_request("query", request)
        self.assertEqual(response.query.code, Constants.OkCode)
        self.assertEqual(response.query.info, "decimal")
        self.assertEqual(response.query.key, b"currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6")
        self.assertEqual(response.query.value, b"123.45")

    async def test_keys_query(self):
        request = Request(query=RequestQuery(path="/keys/currency.balances"))
        response = await self.process_request("query", request)
        self.assertEqual(response.query.code, Constants.OkCode)
        self.assertEqual(response.query.info, "str")
        self.assertEqual(response.query.key, b"currency.balances")
        self.assertEqual(response.query.value, b'["c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"]')

    async def test_estimate_stamps_query(self):
        encoded_payload = "7b226d65746164617461223a7b227369676e6174757265223a226662333466663762383465623535386464366438623265343330323662326265646565363935346665353631616436326336636164346164373366323866313466323832643565366561663966663062343165613865643731346662313832626263346463383161636563356566626331363462343064326131393835373039227d2c227061796c6f6164223a7b22636861696e5f6964223a227869616e2d746573746e65742d31222c22636f6e7472616374223a227375626d697373696f6e222c2266756e6374696f6e223a227375626d69745f636f6e7472616374222c226b7761726773223a7b22636f6465223a225c6e23204c53543030315c6e62616c616e636573203d20486173682864656661756c745f76616c75653d30295c6e5c6e23204c53543030325c6e6d65746164617461203d204861736828295c6e5c6e40636f6e7374727563745c6e646566207365656428293a5c6e2020202023204c5354303031202d204d494e5420535550504c5920746f2077616c6c65742074686174207375626d6974732074686520636f6e74726163745c6e2020202062616c616e6365735b6374782e63616c6c65725d203d20315f3030305f3030305c6e5c6e2020202023204c53543030325c6e202020206d657461646174615b27746f6b656e5f6e616d65275d203d205c22526f636b657473776170205465737420546f6b656e5c225c6e202020206d657461646174615b27746f6b656e5f73796d626f6c275d203d205c22525357505c225c6e2020202023206d657461646174615b27746f6b656e5f6c6f676f5f75726c275d203d202768747470733a2f2f736f6d652e746f6b656e2e75726c2f746573742d746f6b656e2e706e67275c6e202020206d657461646174615b276f70657261746f72275d203d206374782e63616c6c65725c6e5c6e23204c53543030325c6e406578706f72745c6e646566206368616e67655f6d65746164617461286b65793a207374722c2076616c75653a20416e79293a5c6e20202020617373657274206374782e63616c6c6572203d3d206d657461646174615b276f70657261746f72275d2c20274f6e6c79206f70657261746f722063616e20736574206d6574616461746121275c6e202020206d657461646174615b6b65795d203d2076616c75655c6e5c6e23204c53543030315c6e406578706f72745c6e646566207472616e7366657228616d6f756e743a20666c6f61742c20746f3a20737472293a5c6e2020202061737365727420616d6f756e74203e20302c202743616e6e6f742073656e64206e656761746976652062616c616e63657321275c6e202020206173736572742062616c616e6365735b6374782e63616c6c65725d203e3d20616d6f756e742c20274e6f7420656e6f75676820636f696e7320746f2073656e6421275c6e5c6e2020202062616c616e6365735b6374782e63616c6c65725d202d3d20616d6f756e745c6e2020202062616c616e6365735b746f5d202b3d20616d6f756e745c6e5c6e23204c53543030315c6e406578706f72745c6e64656620617070726f766528616d6f756e743a20666c6f61742c20746f3a20737472293a5c6e2020202061737365727420616d6f756e74203e20302c202743616e6e6f742073656e64206e656761746976652062616c616e63657321275c6e2020202062616c616e6365735b6374782e63616c6c65722c20746f5d202b3d20616d6f756e745c6e5c6e23204c53543030315c6e406578706f72745c6e646566207472616e736665725f66726f6d28616d6f756e743a20666c6f61742c20746f3a207374722c206d61696e5f6163636f756e743a20737472293a5c6e2020202061737365727420616d6f756e74203e20302c202743616e6e6f742073656e64206e656761746976652062616c616e63657321275c6e202020206173736572742062616c616e6365735b6d61696e5f6163636f756e742c206374782e63616c6c65725d203e3d20616d6f756e742c20274e6f7420656e6f75676820636f696e7320617070726f76656420746f2073656e642120596f752068617665207b7d20616e642061726520747279696e6720746f207370656e64207b7d2720202020202020202e666f726d61742862616c616e6365735b6d61696e5f6163636f756e742c206374782e63616c6c65725d2c20616d6f756e74295c6e202020206173736572742062616c616e6365735b6d61696e5f6163636f756e745d203e3d20616d6f756e742c20274e6f7420656e6f75676820636f696e7320746f2073656e6421275c6e5c6e2020202062616c616e6365735b6d61696e5f6163636f756e742c206374782e63616c6c65725d202d3d20616d6f756e745c6e2020202062616c616e6365735b6d61696e5f6163636f756e745d202d3d20616d6f756e745c6e2020202062616c616e6365735b746f5d202b3d20616d6f756e745c6e222c226e616d65223a22636f6e5f74657374696e675f7375626d697373696f6e5f3836343932393539227d2c226e6f6e6365223a362c2273656e646572223a2265396538616164323963653865393466643737643963353535383265356530633537636638316335353262613631633064346533346230646331316664393331222c227374616d70735f737570706c696564223a35303030307d7d"
        request = Request(query=RequestQuery(path=f"/calculate_stamps/{encoded_payload}"))
        response = await self.process_request("query", request)
        result = json.loads(response.query.value)
        self.assertEqual(response.query.code, Constants.OkCode)
        # self.assertEqual(response.query.info, "str")
        self.assertEqual(response.query.key.decode(), encoded_payload)
        self.assertEqual(result["status"], Constants.OkCode)
        # Accounting for the fact that the stamp calculation is not deterministic between different architectures e.g (M2 Max vs AMD64).
        # However, in the blockchain environment the stamp calculation is deterministic.
        self.assertGreater(result["stamps_used"], 200)


    async def test_health_query(self):
        
        request = Request(query=RequestQuery(path="/health"))
        response = await self.process_request("query", request)
        self.assertEqual(response.query.code, Constants.OkCode)
        self.assertEqual(response.query.info, "str")
        self.assertEqual(response.query.key, b"")
        self.assertEqual(response.query.value, b"OK")

    async def test_get_next_nonce_query(self):
        request = Request(query=RequestQuery(path="/get_next_nonce/c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"))
        response = await self.process_request("query", request)
        self.assertEqual(response.query.code, Constants.OkCode)
        self.assertEqual(response.query.info, "int")
        self.assertEqual(response.query.key, b"c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6")
        self.assertEqual(response.query.value, b"0")

    async def test_contract_query(self):
        request = Request(query=RequestQuery(path="/contract/currency"))
        response = await self.process_request("query", request)
        self.assertEqual(response.query.code, Constants.OkCode)
        self.assertEqual(response.query.info, "str")

    async def test_contract_methods_query(self):
        request = Request(query=RequestQuery(path="/contract_methods/currency"))
        response = await self.process_request("query", request)
        self.assertEqual(response.query.code, Constants.OkCode)
        self.assertEqual(response.query.info, "str")

    async def test_contract_vars_query(self):
        request = Request(query=RequestQuery(path="/contract_vars/currency"))
        response = await self.process_request("query", request)
        self.assertEqual(response.query.code, Constants.OkCode)
        self.assertEqual(response.query.info, "str")

if __name__ == "__main__":
    unittest.main()