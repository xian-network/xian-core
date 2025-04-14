import os
import unittest
import json
from io import BytesIO
import logging
import sys
from pathlib import Path
import tempfile
import shutil
import datetime
import math

from xian.utils.block import set_latest_block_hash
from contracting.stdlib.bridge.time import Datetime

from fixtures.mock_constants import MockConstants
import pytest

from xian.constants import Constants as c
from xian.xian_abci import Xian
from xian.utils.state_patches import StatePatchManager
from abci.server import ProtocolHandler
from abci.utils import read_messages

from cometbft.abci.v1beta3.types_pb2 import (
    Request,
    Response,
    ResponseFinalizeBlock,
    RequestFinalizeBlock,
)
from google.protobuf.timestamp_pb2 import Timestamp

from utils import setup_fixtures, teardown_fixtures

# Disable any kind of logging
logging.disable(logging.CRITICAL)

async def deserialize(raw: bytes) -> Response:
    try:
        resp = next(read_messages(BytesIO(raw), Response))
        return resp
    except Exception as e:
        logging.error("Deserialization error: %s", e)
        raise

class TestABCIStatePatch(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        setup_fixtures()
        
        # Create a temporary state patches file for testing
        self.patches_dir = Path("/tmp/xian_test_state_patches")
        self.patches_dir.mkdir(exist_ok=True)
        
        self.patches_file = self.patches_dir / "state_patches.json"
        self.test_patches = {
            "10": [
                {
                    "key": "test_contract.test_value",
                    "value": "patched_value_1",
                    "comment": "Test patch at block 10"
                }
            ],
            "20": [
                {
                    "key": "test_contract.test_dict",
                    "value": {"key1": "value1", "key2": 42},
                    "comment": "Test patch with dict at block 20"
                }
            ]
        }
        
        with open(self.patches_file, "w") as f:
            json.dump(self.test_patches, f)
        
        # Initialize Xian app with our test patches
        self.app = await Xian.create(constants=MockConstants)
        
        # Override the state patch manager to use our test file
        self.app.state_patch_manager = StatePatchManager(self.app.client.raw_driver)
        self.app.state_patch_manager.load_patches(self.patches_file)
        
        # Initialize other test variables
        self.handler = ProtocolHandler(self.app)
    
    async def asyncTearDown(self):
        teardown_fixtures()
        
        # Clean up our temporary files
        if self.patches_dir.exists():
            shutil.rmtree(self.patches_dir)
    
    async def process_request(self, request_type, req):
        raw = await self.handler.process(request_type, req)
        resp = await deserialize(raw)
        return resp
    
    def create_finalize_block_request(self, height, time_seconds=0):
        """Helper method to create a finalize block request with given height"""
        timestamp = Timestamp()
        timestamp.seconds = time_seconds
        
        return Request(finalize_block=RequestFinalizeBlock(
            height=height,
            time=timestamp,
            txs=[],  # No transactions for simplicity
            hash=b"test_hash"
        ))
    
    def get_now_from_nanos(self, nanos):
        """Convert nanos to a Datetime object, just like the processor does."""
        return Datetime._from_datetime(
            datetime.datetime.utcfromtimestamp(math.ceil(nanos / 1e9))
        )
    
    def create_execution_environment(self, app):
        """Helper method to create an execution environment for contracts"""
        # Convert nanos from block timestamp to a proper Datetime object
        now_datetime = self.get_now_from_nanos(app.current_block_meta["nanos"])
        
        return {
            'now': now_datetime,
            'block_num': app.current_block_meta["height"],
            'chain_id': app.current_block_meta["chain_id"]
        }
    
    async def test_patches_loaded_correctly(self):
        """Test that the state patches file is loaded correctly"""
        self.assertTrue(self.app.state_patch_manager.loaded)
        self.assertEqual(len(self.app.state_patch_manager.patches), 2)
        self.assertIn(10, self.app.state_patch_manager.patches)
        self.assertIn(20, self.app.state_patch_manager.patches)
    
    async def test_patch_applied_at_correct_block(self):
        """Test that patches are applied at the correct block height"""
        # Set up block 9 (before patch)
        self.app.current_block_meta = {"height": 9, "nanos": 0, "chain_id": "test"}
        request_9 = self.create_finalize_block_request(9)
        response_9 = await self.process_request("finalize_block", request_9)
        
        # No patch should be applied at block 9
        self.assertIsNone(self.app.client.raw_driver.get("test_contract.test_value"))
        
        # Set up block 10 (patch should apply)
        self.app.current_block_meta = {"height": 10, "nanos": 0, "chain_id": "test"}
        request_10 = self.create_finalize_block_request(10)
        response_10 = await self.process_request("finalize_block", request_10)
        
        # Check that the patch was applied
        self.assertEqual(
            self.app.client.raw_driver.get("test_contract.test_value"), 
            "patched_value_1"
        )
        
        # Set up block 20 (second patch should apply)
        self.app.current_block_meta = {"height": 20, "nanos": 0, "chain_id": "test"}
        request_20 = self.create_finalize_block_request(20)
        response_20 = await self.process_request("finalize_block", request_20)
        
        # Check that the second patch was applied
        self.assertEqual(
            self.app.client.raw_driver.get("test_contract.test_dict"), 
            {"key1": "value1", "key2": 42}
        )
    
    async def test_app_hash_updated_with_patch(self):
        """Test that the app hash is updated when a patch is applied"""
        # Get app hash at block 9 (before patch)
        self.app.current_block_meta = {"height": 9, "nanos": 0, "chain_id": "test"}
        request_9 = self.create_finalize_block_request(9)
        response_9 = await self.process_request("finalize_block", request_9)
        app_hash_9 = response_9.finalize_block.app_hash
        set_latest_block_hash(app_hash_9)
        
        # Get app hash at block 10 (with patch)
        self.app.current_block_meta = {"height": 10, "nanos": 0, "chain_id": "test"}
        request_10 = self.create_finalize_block_request(10)
        response_10 = await self.process_request("finalize_block", request_10)
        app_hash_10 = response_10.finalize_block.app_hash
        set_latest_block_hash(app_hash_10)
        
        
        # App hash should be different when patch is applied
        self.assertNotEqual(app_hash_9, app_hash_10, "App hash should change when a state patch is applied")
        
        # Get app hash at block 11 (no patch)
        self.app.current_block_meta = {"height": 11, "nanos": 0, "chain_id": "test"}
        request_11 = self.create_finalize_block_request(11)
        response_11 = await self.process_request("finalize_block", request_11)
        app_hash_11 = response_11.finalize_block.app_hash
        set_latest_block_hash(app_hash_11)
        
        # App hash should remain the same if no patch or transaction
        self.assertEqual(app_hash_10, app_hash_11, "App hash should remain unchanged if no state change")
        
        # Process another block with an added state value
        self.app.client.raw_driver.set("test_contract.manual_value", "manual_test")
        self.app.current_block_meta = {"height": 12, "nanos": 0, "chain_id": "test"}
        request_12 = self.create_finalize_block_request(12)
        response_12 = await self.process_request("finalize_block", request_12)
        app_hash_12 = response_12.finalize_block.app_hash
        
        # App hash should still remain the same (since we're not adding the manual change to fingerprint hashes)
        self.assertEqual(app_hash_11, app_hash_12, "App hash should remain unchanged for manual state changes outside fingerprint")
    
    async def test_no_patch_normal_operation(self):
        """Test that everything continues normally when no patch is present"""
        # Set a test value directly
        self.app.client.raw_driver.set("test_contract.normal_value", "normal_test")
        
        # Process block 15 (no patch at this height)
        self.app.current_block_meta = {"height": 15, "nanos": 0, "chain_id": "test"}
        request_15 = self.create_finalize_block_request(15)
        response_15 = await self.process_request("finalize_block", request_15)
        
        # Verify the value we set is still there
        self.assertEqual(
            self.app.client.raw_driver.get("test_contract.normal_value"), 
            "normal_test"
        )
        
        # Verify we get a successful response
        self.assertIsNotNone(response_15.finalize_block.app_hash)
    
    async def test_missing_patches_file(self):
        """Test that the system handles a missing patches file gracefully"""
        # Create a new app with no patches file
        new_app = await Xian.create(constants=MockConstants)
        
        # Override the state patch manager path to a non-existent file
        new_app.state_patch_manager = StatePatchManager(new_app.client.raw_driver)
        non_existent_file = Path("/tmp/non_existent_file.json")
        new_app.state_patch_manager.load_patches(non_existent_file)
        
        # The manager should still be marked as loaded (just with no patches)
        self.assertTrue(new_app.state_patch_manager.loaded)
        self.assertEqual(len(new_app.state_patch_manager.patches), 0)
        
        # Process a block - should work normally
        new_handler = ProtocolHandler(new_app)
        new_app.current_block_meta = {"height": 10, "nanos": 0, "chain_id": "test"}
        request = self.create_finalize_block_request(10)
        raw = await new_handler.process("finalize_block", request)
        resp = await deserialize(raw)
        
        # Should get a valid response
        self.assertIsNotNone(resp.finalize_block.app_hash)

    async def test_contract_code_patch_compilation(self):
        """Test that contract code patches are properly compiled and are functional"""
        # Create a temporary state patches file with a contract code patch
        self.patches_dir = Path("/tmp/xian_test_state_patches")
        self.patches_dir.mkdir(exist_ok=True)
        
        # Import necessary components for proper contract compilation
        from contracting.compilation.compiler import ContractingCompiler
        import marshal
        import binascii
        
        # Sample contract code - without depending on constructor execution
        contract_code = """
# Contract code for testing
balances = Hash(default_value=0)

@export
def transfer(amount: int, to: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send!'
    
    balances[ctx.caller] -= amount
    balances[to] += amount
    
@export
def get_balance(account: str):
    return balances[account]
"""
        
        # Create a patch file with contract code entry and initial balance state
        # Let the StatePatchManager handle compilation
        contract_patch = {
            "30": [
                {
                    "key": "con_test_token.__code__",
                    "value": contract_code,
                    "comment": "Test contract code patch - the patch manager will compile this"
                },
                {
                    "key": "con_test_token.balances:contract_owner",
                    "value": 1000,
                    "comment": "Initialize balance state (would normally be set by constructor)"
                }
            ]
        }
        
        contract_patch_file = self.patches_dir / "contract_patches.json"
        with open(contract_patch_file, "w") as f:
            json.dump(contract_patch, f)
        
        # Initialize a new app with the contract patches
        new_app = await Xian.create(constants=MockConstants)
        new_app.state_patch_manager = StatePatchManager(new_app.client.raw_driver)
        new_app.state_patch_manager.load_patches(contract_patch_file)
        
        # Process block 30 to apply the patch
        new_handler = ProtocolHandler(new_app)
        new_app.current_block_meta = {"height": 30, "nanos": 0, "chain_id": "test"}
        request_30 = self.create_finalize_block_request(30)
        await new_handler.process("finalize_block", request_30)
        
        # No need to submit the contract again - it's already loaded via the state patch
        
        # Verify that both the code and compiled code were set
        self.assertIsNotNone(new_app.client.raw_driver.get("con_test_token.__code__"))
        self.assertIsNotNone(new_app.client.raw_driver.get("con_test_token.__compiled__"))
        
        # Note: The stored code will be the transformed code, not the original source code
        stored_code = new_app.client.raw_driver.get("con_test_token.__code__")
        self.assertIn("balances", stored_code, "Transformed code should contain the balances variable")
        # We don't do an exact comparison since the transformed code will include privatization and other changes
        
        # Now verify that the contract actually works by executing its functions
        
        # First, check if the initial balance state was set correctly
        owner_balance = new_app.client.get_var(
            contract='con_test_token',
            variable='balances',
            arguments=['contract_owner']
        )
        self.assertEqual(owner_balance, 1000, "Initial balance state should have been set by the state patch")
        
        # Now simulate a transfer
        test_sender = 'contract_owner'
        test_receiver = 'test_receiver'
        test_amount = 100
        
        # Execute the transfer using the client's executor
        result = new_app.client.executor.execute(
            sender=test_sender,
            contract_name='con_test_token',
            function_name='transfer',
            kwargs={
                'amount': test_amount,
                'to': test_receiver
            },
            environment=self.create_execution_environment(new_app)
        )
        
        # Now apply the state changes using the raw_driver
        for key, value in result['writes'].items():
            new_app.client.raw_driver.set(key, value)
        
        # Apply changes with a timestamp to finalize them
        new_app.client.raw_driver.hard_apply(new_app.current_block_meta["nanos"])
        
        # Verify that balances were updated correctly
        sender_balance = new_app.client.get_var(
            contract='con_test_token',
            variable='balances',
            arguments=[test_sender]
        )
        receiver_balance = new_app.client.get_var(
            contract='con_test_token',
            variable='balances',
            arguments=[test_receiver]
        )
        
        self.assertEqual(sender_balance, 900, "Sender balance should be decreased by the transfer amount")
        self.assertEqual(receiver_balance, 100, "Receiver balance should be increased by the transfer amount")
        
        # Also test the get_balance method
        retrieved_balance = new_app.client.executor.execute(
            sender='anyone',
            contract_name='con_test_token',
            function_name='get_balance',
            kwargs={
                'account': test_receiver
            },
            environment=self.create_execution_environment(new_app)
        )['result']
        
        self.assertEqual(retrieved_balance, 100, "get_balance method should return the correct balance")

    async def test_updating_existing_contract(self):
        """Test that contract code patches can update an existing contract."""
        # Create a temporary state patches file with a contract code patch
        self.patches_dir = Path("/tmp/xian_test_state_patches")
        self.patches_dir.mkdir(exist_ok=True)
        
        # Define original contract version
        original_contract_code = """
# Original contract code
balances = Hash(default_value=0)

@export
def transfer(amount: int, to: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send!'
    
    balances[ctx.caller] -= amount
    balances[to] += amount
"""
        
        # Define updated contract version with a new method
        updated_contract_code = """
# Updated contract code
balances = Hash(default_value=0)

@export
def transfer(amount: int, to: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send!'
    
    balances[ctx.caller] -= amount
    balances[to] += amount
    
@export
def get_balance(account: str):
    return balances[account]
"""
        
        # Create a patch file with initial contract at block 30 and update at block 40
        contract_patches = {
            "30": [
                {
                    "key": "con_update_test.__code__",
                    "value": original_contract_code,
                    "comment": "Initial contract deployment"
                },
                {
                    "key": "con_update_test.balances:contract_owner",
                    "value": 1000,
                    "comment": "Initialize balance state"
                }
            ],
            "40": [
                {
                    "key": "con_update_test.__code__",
                    "value": updated_contract_code,
                    "comment": "Contract update adding get_balance method"
                }
            ]
        }
        
        update_patch_file = self.patches_dir / "update_patches.json"
        with open(update_patch_file, "w") as f:
            json.dump(contract_patches, f)
        
        # Initialize a new app with the contract patches
        new_app = await Xian.create(constants=MockConstants)
        new_app.state_patch_manager = StatePatchManager(new_app.client.raw_driver)
        new_app.state_patch_manager.load_patches(update_patch_file)
        
        # Process block 30 to deploy initial contract
        new_handler = ProtocolHandler(new_app)
        new_app.current_block_meta = {"height": 30, "nanos": 0, "chain_id": "test"}
        request_30 = self.create_finalize_block_request(30)
        await new_handler.process("finalize_block", request_30)
        
        # Verify original contract works
        try:
            # The method should not exist in original version
            result = new_app.client.executor.execute(
                sender='anyone',
                contract_name='con_update_test',
                function_name='get_balance',
                kwargs={'account': 'contract_owner'},
                environment=self.create_execution_environment(new_app)
            )
            self.fail("Expected get_balance to not exist yet")
        except Exception as e:
            # Should get an exception because the method doesn't exist yet
            self.assertIn("get_balance", str(e))
        
        # Process block 40 to apply contract update
        new_app.current_block_meta = {"height": 40, "nanos": 0, "chain_id": "test"}
        request_40 = self.create_finalize_block_request(40)
        await new_handler.process("finalize_block", request_40)
        
        # Verify the updated contract has the new method and old state is preserved
        # Check if the balance state was preserved
        owner_balance = new_app.client.get_var(
            contract='con_update_test',
            variable='balances',
            arguments=['contract_owner']
        )
        self.assertEqual(owner_balance, 1000, "Balance state should be preserved after contract update")
        
        # Now the get_balance method should exist and work
        result = new_app.client.executor.execute(
            sender='anyone',
            contract_name='con_update_test',
            function_name='get_balance',
            kwargs={'account': 'contract_owner'},
            environment=self.create_execution_environment(new_app)
        )
        self.assertEqual(result['result'], 1000, "New get_balance method should work after update")
    
    async def test_error_handling_invalid_contract(self):
        """Test how the system handles invalid contract code in patches."""
        # Create a temporary state patches file with invalid contract code
        self.patches_dir = Path("/tmp/xian_test_state_patches")
        self.patches_dir.mkdir(exist_ok=True)
        
        # Define contract with syntax error
        syntax_error_contract = """
# Contract with syntax error
balances = Hash(default_value=0)

@export
def transfer(amount: int, to: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send!'
    
    # Missing colon in if statement - syntax error
    if amount > 100
        return False
    
    balances[ctx.caller] -= amount
    balances[to] += amount
    return True
"""
        
        # Define contract with linting error (missing type annotations)
        linting_error_contract = """
# Contract with linting error
balances = Hash(default_value=0)

@export
def transfer(amount, to):  # Missing type annotations - linting error
    assert amount > 0, 'Cannot send negative balances!'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send!'
    
    balances[ctx.caller] -= amount
    balances[to] += amount
    return True
"""
        
        # Create patches with both error types
        error_patches = {
            "50": [
                {
                    "key": "con_syntax_error.__code__",
                    "value": syntax_error_contract,
                    "comment": "Contract with syntax error"
                }
            ],
            "60": [
                {
                    "key": "con_linting_error.__code__",
                    "value": linting_error_contract,
                    "comment": "Contract with linting error"
                }
            ]
        }
        
        error_patch_file = self.patches_dir / "error_patches.json"
        with open(error_patch_file, "w") as f:
            json.dump(error_patches, f)
        
        # Initialize a new app with the contract patches
        new_app = await Xian.create(constants=MockConstants)
        new_app.state_patch_manager = StatePatchManager(new_app.client.raw_driver)
        new_app.state_patch_manager.load_patches(error_patch_file)
        
        # Process block 50 - should handle syntax error gracefully
        new_handler = ProtocolHandler(new_app)
        new_app.current_block_meta = {"height": 50, "nanos": 0, "chain_id": "test"}
        request_50 = self.create_finalize_block_request(50)
        
        # Should not raise exception but log the error
        await new_handler.process("finalize_block", request_50)
        
        # The contract should not be set in state due to syntax error
        self.assertIsNone(new_app.client.raw_driver.get("con_syntax_error.__code__"))
        
        # Process block 60 - should handle linting error gracefully
        new_app.current_block_meta = {"height": 60, "nanos": 0, "chain_id": "test"}
        request_60 = self.create_finalize_block_request(60)
        
        # Should not raise exception but log the error
        await new_handler.process("finalize_block", request_60)
        
        # The contract should not be set in state due to linting error
        self.assertIsNone(new_app.client.raw_driver.get("con_linting_error.__code__"))
    
    async def test_multiple_contract_patches_same_block(self):
        """Test applying multiple contract code patches at the same block height."""
        # Create a temporary state patches file with multiple contracts at same block
        self.patches_dir = Path("/tmp/xian_test_state_patches")
        self.patches_dir.mkdir(exist_ok=True)
        
        # Define first contract
        contract_code_1 = """
# First contract
token_name = Variable()
token_symbol = Variable()
balances = Hash(default_value=0)

@construct
def seed():
    token_name.set("First Token")
    token_symbol.set("TK1")

@export
def transfer(amount: int, to: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send!'
    
    balances[ctx.caller] -= amount
    balances[to] += amount
    return True
"""
        
        # Define second contract
        contract_code_2 = """
# Second contract
token_name = Variable()
token_symbol = Variable()
balances = Hash(default_value=0)

@construct
def seed():
    token_name.set("Second Token")
    token_symbol.set("TK2")

@export
def transfer(amount: int, to: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send!'
    
    balances[ctx.caller] -= amount
    balances[to] += amount
    return True
"""
        
        # Create patches with both contracts at the same block height
        multi_patches = {
            "70": [
                {
                    "key": "con_token1.__code__",
                    "value": contract_code_1,
                    "comment": "First token contract"
                },
                {
                    "key": "con_token1.balances:contract_owner",
                    "value": 1000,
                    "comment": "Initialize first token balance"
                },
                {
                    "key": "con_token2.__code__",
                    "value": contract_code_2,
                    "comment": "Second token contract"
                },
                {
                    "key": "con_token2.balances:contract_owner",
                    "value": 2000,
                    "comment": "Initialize second token balance"
                }
            ]
        }
        
        multi_patch_file = self.patches_dir / "multi_patches.json"
        with open(multi_patch_file, "w") as f:
            json.dump(multi_patches, f)
        
        # Initialize a new app with the contract patches
        new_app = await Xian.create(constants=MockConstants)
        new_app.state_patch_manager = StatePatchManager(new_app.client.raw_driver)
        new_app.state_patch_manager.load_patches(multi_patch_file)
        
        # Process block 70 to apply both contracts
        new_handler = ProtocolHandler(new_app)
        new_app.current_block_meta = {"height": 70, "nanos": 0, "chain_id": "test"}
        request_70 = self.create_finalize_block_request(70)
        await new_handler.process("finalize_block", request_70)
        
        # Verify both contracts were deployed and work correctly
        # Both contracts should be in state
        self.assertIsNotNone(new_app.client.raw_driver.get("con_token1.__code__"))
        self.assertIsNotNone(new_app.client.raw_driver.get("con_token2.__code__"))
        
        # Verify initial balances for both tokens
        token1_balance = new_app.client.get_var(
            contract='con_token1',
            variable='balances',
            arguments=['contract_owner']
        )
        self.assertEqual(token1_balance, 1000, "First token balance should be initialized")
        
        token2_balance = new_app.client.get_var(
            contract='con_token2',
            variable='balances',
            arguments=['contract_owner']
        )
        self.assertEqual(token2_balance, 2000, "Second token balance should be initialized")
    
    async def test_contract_with_dependencies(self):
        """Test contract patches where one contract depends on another."""
        # Create a temporary state patches file with a contract code patch
        self.patches_dir = Path("/tmp/xian_test_state_patches")
        self.patches_dir.mkdir(exist_ok=True)
        
        # Define base contract (currency)
        currency_contract = """
# Currency contract
balances = Hash(default_value=0)

@export
def transfer(amount: int, to: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send!'
    
    balances[ctx.caller] -= amount
    balances[to] += amount
    return True

@export
def balance_of(account: str):
    return balances[account]
"""
        
        # Define dependent contract (exchange) that imports the currency contract
        exchange_contract = """
# Exchange contract that depends on currency
import con_currency

pairs = Hash(default_value=0)

@export
def create_market(base: str, quote: str, price: int):
    # Create trading pair
    pair_key = f"{base}_{quote}"
    pairs[pair_key] = price
    return True

@export
def buy(base: str, quote: str, amount: int):
    # Use currency contract to execute trade
    pair_key = f"{base}_{quote}"
    price = pairs[pair_key]
    
    cost = amount * price
    
    # Transfer quote currency from buyer to seller
    con_currency.transfer(amount=cost, to="market")
    
    return True
"""
        
        # Create patch file with both contracts
        dependency_patches = {
            "80": [
                {
                    "key": "con_currency.__code__",
                    "value": currency_contract,
                    "comment": "Base currency contract"
                },
                {
                    "key": "con_currency.balances:trader1",
                    "value": 10000,
                    "comment": "Initialize trader1 balance"
                }
            ],
            "81": [
                {
                    "key": "con_exchange.__code__",
                    "value": exchange_contract,
                    "comment": "Exchange contract that depends on currency"
                }
            ]
        }
        
        dependency_patch_file = self.patches_dir / "dependency_patches.json"
        with open(dependency_patch_file, "w") as f:
            json.dump(dependency_patches, f)
        
        # Initialize a new app with the contract patches
        new_app = await Xian.create(constants=MockConstants)
        new_app.state_patch_manager = StatePatchManager(new_app.client.raw_driver)
        new_app.state_patch_manager.load_patches(dependency_patch_file)
        
        # Process block 80 to deploy currency contract
        new_handler = ProtocolHandler(new_app)
        new_app.current_block_meta = {"height": 80, "nanos": 0, "chain_id": "test"}
        request_80 = self.create_finalize_block_request(80)
        await new_handler.process("finalize_block", request_80)
        
        # Process block 81 to deploy exchange contract
        new_app.current_block_meta = {"height": 81, "nanos": 0, "chain_id": "test"}
        request_81 = self.create_finalize_block_request(81)
        await new_handler.process("finalize_block", request_81)
        
        # Verify both contracts were deployed
        self.assertIsNotNone(new_app.client.raw_driver.get("con_currency.__code__"))
        self.assertIsNotNone(new_app.client.raw_driver.get("con_exchange.__code__"))
        
        # Verify the exchange contract can create a market
        result = new_app.client.executor.execute(
            sender='trader1',
            contract_name='con_exchange',
            function_name='create_market',
            kwargs={
                'base': 'BTC', 
                'quote': 'USD',
                'price': 50000
            },
            environment=self.create_execution_environment(new_app)
        )
        
        # Apply the changes
        for key, value in result['writes'].items():
            new_app.client.raw_driver.set(key, value)
        new_app.client.raw_driver.hard_apply(new_app.current_block_meta["nanos"])
        
        # Verify the market was created
        pair_value = new_app.client.get_var(
            contract='con_exchange',
            variable='pairs',
            arguments=['BTC_USD']
        )
        self.assertEqual(pair_value, 50000, "Market should be created with correct price")
    
    async def test_complex_orm_structures(self):
        """Test contract with various ORM types to ensure proper transformation."""
        # Create a temporary state patches file with a contract using complex ORM
        self.patches_dir = Path("/tmp/xian_test_state_patches")
        self.patches_dir.mkdir(exist_ok=True)
        
        # Define a contract with multiple ORM types
        complex_orm_contract = """
# Contract with complex ORM structures
token_name = Variable()  # Simple variable
token_symbol = Variable()
total_supply = Variable()

# A regular hash for balances
balances = Hash(default_value=0)

# A hash for allowances with nested keys
allowances = Hash(default_value=0)

# A hash for metadata
metadata = Hash()

# A hash for tracking user activity
user_activity = Hash(default_value=[])

@export
def transfer(amount: int, to: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send!'
    
    balances[ctx.caller] -= amount
    balances[to] += amount
    
    # Track activity with nested hash usage
    activity = user_activity[ctx.caller] or []
    activity.append({
        'type': 'transfer',
        'amount': amount,
        'to': to,
        'timestamp': now
    })
    user_activity[ctx.caller] = activity
    
    # Maintain a nested mapping for historical transfers
    allowances[ctx.caller, to] = allowances[ctx.caller, to] + amount
    
    # Use metadata hash with non-default types
    metadata[ctx.caller, to, amount] = {
        'timestamp': now,
        'memo': 'Transfer completed'
    }
    
    return True

@export
def get_allowance(owner: str, spender: str):
    return allowances[owner, spender]
"""
        
        # Create patch file with the complex ORM contract
        orm_patches = {
            "90": [
                {
                    "key": "con_complex_orm.__code__",
                    "value": complex_orm_contract,
                    "comment": "Contract with complex ORM structures"
                },
                {
                    "key": "con_complex_orm.token_name",
                    "value": "Complex Token",
                    "comment": "Set token name"
                },
                {
                    "key": "con_complex_orm.token_symbol",
                    "value": "CPX",
                    "comment": "Set token symbol"
                },
                {
                    "key": "con_complex_orm.total_supply",
                    "value": 1000000,
                    "comment": "Set total supply"
                },
                {
                    "key": "con_complex_orm.balances:contract_owner",
                    "value": 1000000,
                    "comment": "Initialize owner balance"
                }
            ]
        }
        
        orm_patch_file = self.patches_dir / "orm_patches.json"
        with open(orm_patch_file, "w") as f:
            json.dump(orm_patches, f)
        
        # Initialize a new app with the contract patches
        new_app = await Xian.create(constants=MockConstants)
        new_app.state_patch_manager = StatePatchManager(new_app.client.raw_driver)
        new_app.state_patch_manager.load_patches(orm_patch_file)
        
        # Process block 90 to deploy the complex ORM contract
        new_handler = ProtocolHandler(new_app)
        new_app.current_block_meta = {"height": 90, "nanos": 0, "chain_id": "test"}
        request_90 = self.create_finalize_block_request(90)
        await new_handler.process("finalize_block", request_90)
        
        # Verify the contract was deployed
        self.assertIsNotNone(new_app.client.raw_driver.get("con_complex_orm.__code__"))
        
        # Verify variable values were set correctly
        token_name = new_app.client.get_var(
            contract='con_complex_orm',
            variable='token_name'
        )
        self.assertEqual(token_name, "Complex Token", "Variable should be set correctly")
        
        # Execute a transfer to test complex ORM operations
        result = new_app.client.executor.execute(
            sender='contract_owner',
            contract_name='con_complex_orm',
            function_name='transfer',
            kwargs={
                'amount': 100,
                'to': 'recipient'
            },
            environment=self.create_execution_environment(new_app)
        )
        
        # Apply the changes
        for key, value in result['writes'].items():
            new_app.client.raw_driver.set(key, value)
        new_app.client.raw_driver.hard_apply(new_app.current_block_meta["nanos"])
        
        # Verify balances were updated
        owner_balance = new_app.client.get_var(
            contract='con_complex_orm',
            variable='balances',
            arguments=['contract_owner']
        )
        self.assertEqual(owner_balance, 999900, "Owner balance should be decreased")
        
        recipient_balance = new_app.client.get_var(
            contract='con_complex_orm',
            variable='balances',
            arguments=['recipient']
        )
        self.assertEqual(recipient_balance, 100, "Recipient balance should be increased")
        
        # Verify nested hash operation worked
        allowance = new_app.client.executor.execute(
            sender='anyone',
            contract_name='con_complex_orm',
            function_name='get_allowance',
            kwargs={
                'owner': 'contract_owner',
                'spender': 'recipient'
            },
            environment=self.create_execution_environment(new_app)
        )['result']
        
        self.assertEqual(allowance, 100, "Nested hash operation should work correctly")

    async def test_contract_privatization(self):
        """Test that non-exported functions cannot be called externally but can be used internally."""
        # Create a temporary state patches file with a contract that has private functions
        self.patches_dir = Path("/tmp/xian_test_state_patches")
        self.patches_dir.mkdir(exist_ok=True)
        
        # Define a contract with both public and private functions
        contract_code = """
# Contract with privatization test
stored_value = Variable()

@export
def public_function():
    return "Public function called"

@export
def call_private():
    return private_function()

def private_function():
    return "This is private"
"""
        
        # Create a patch file with the privatization test contract
        privatization_patch = {
            "50": [
                {
                    "key": "con_privatization_test.__code__",
                    "value": contract_code,
                    "comment": "Test contract for privatization"
                }
            ]
        }
        
        privatization_patch_file = self.patches_dir / "privatization_patches.json"
        with open(privatization_patch_file, "w") as f:
            json.dump(privatization_patch, f)
        
        # Initialize a new app with the contract patches
        new_app = await Xian.create(constants=MockConstants)
        new_app.state_patch_manager = StatePatchManager(new_app.client.raw_driver)
        new_app.state_patch_manager.load_patches(privatization_patch_file)
        
        # Process block 50 to apply the patch
        new_handler = ProtocolHandler(new_app)
        new_app.current_block_meta = {"height": 50, "nanos": 0, "chain_id": "test"}
        request_50 = self.create_finalize_block_request(50)
        await new_handler.process("finalize_block", request_50)
        
        # Verify that the contract code was set
        stored_code = new_app.client.raw_driver.get("con_privatization_test.__code__")

        self.assertIsNotNone(stored_code)
        
        # Test 1: Calling a public function directly - should succeed
        public_result = new_app.client.executor.execute(
            sender='test_user',
            contract_name='con_privatization_test',
            function_name='public_function',
            kwargs={},
            environment=self.create_execution_environment(new_app)
        )
        
        self.assertEqual(public_result['result'], "Public function called", 
                         "Public function should be directly callable")
        
        # Test 2: Calling a private function through a public function - should succeed
        indirect_result = new_app.client.executor.execute(
            sender='test_user',
            contract_name='con_privatization_test',
            function_name='call_private',
            kwargs={},
            environment=self.create_execution_environment(new_app)
        )
        self.assertEqual(indirect_result['result'], "This is private", 
                         "Private function should be callable through a public function")
        
        # Test 3: Calling a private function directly - should fail with specific error
        private_result = new_app.client.executor.execute(
            sender='test_user',
            contract_name='con_privatization_test',
            function_name='private_function',
            kwargs={},
            environment=self.create_execution_environment(new_app)
        )
        
        # Verify error status code
        self.assertEqual(private_result['status_code'], 1, "Status code should indicate error")
        
        # Verify exact AttributeError format in the result
        self.assertIsInstance(private_result['result'], AttributeError, 
                            "Error should be an AttributeError")
        self.assertEqual(str(private_result['result']), 
                       "module 'con_privatization_test' has no attribute 'private_function'",
                       "Error message should indicate that the private function is not accessible")
        
        # Verify code transformation in reads
        transformed_code = private_result['reads']['con_privatization_test.__code__']
        self.assertIn('__private_function', transformed_code, 
                     "Private function should be renamed with double underscore prefix")
        self.assertIn("@__export('con_privatization_test')", transformed_code, 
                     "Export decorator should be transformed correctly")

if __name__ == "__main__":
    unittest.main() 