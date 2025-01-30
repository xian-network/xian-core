import json
import os
from pathlib import Path
import pytest
from xian.tools.genesis_upgrades.approvals_upgrade import (
    find_xsc001_tokens,
    migrate_approvals,
    process_genesis_data,
)


@pytest.fixture
def genesis_data():
    """Load the test genesis file"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    genesis_path = fixtures_dir / "genesis.json"

    with open(genesis_path, "r") as f:
        return json.load(f)


@pytest.fixture
def sample_token_genesis():
    """Create a sample genesis with token contracts and approvals"""
    return {
        "abci_genesis": {
            "genesis": [
                {
                    "key": "con_token1.__code__",
                    "value": """
__balances = Hash(default_value=0)
__metadata = Hash(default_value='')
def transfer(amount, to): pass
def approve(amount, to): pass
def transfer_from(amount, to, main_account): pass
                    """,
                },
                {"key": "con_token1.balances:wallet1:wallet2", "value": "100"},
                {
                    "key": "con_token1.balances:wallet3",  # Regular balance, should not be changed
                    "value": "500",
                },
                {
                    "key": "con_pixel_token.__code__",  # Should be ignored (pixel token)
                    "value": """
__balances = Hash(default_value=0)
__metadata = Hash(default_value='')
def transfer(amount, to): pass
def approve(amount, to): pass
def transfer_from(amount, to, main_account): pass
                    """,
                },
                {
                    "key": "con_pixel_token.balances:wallet1:wallet2",  # Should be ignored
                    "value": "100",
                },
                {
                    "key": "currency.__code__",
                    "value": """
__balances = Hash(default_value=0)
__metadata = Hash(default_value='')
def transfer(amount, to): pass
def approve(amount, to): pass
def transfer_from(amount, to, main_account): pass
                    """,
                },
                {"key": "currency.balances:wallet1:wallet2", "value": "100"},
            ]
        }
    }


def test_find_xsc001_tokens(sample_token_genesis):
    tokens = find_xsc001_tokens(sample_token_genesis)
    assert tokens == ["con_token1", "currency"]
    assert "con_pixel_token" not in tokens


def test_migrate_approvals(sample_token_genesis):
    tokens = ["con_token1", "currency"]
    updated_genesis, changes_made = migrate_approvals(
        sample_token_genesis, tokens
    )

    # Check that changes were made
    assert changes_made == True

    # Get all keys in the updated genesis
    keys = [
        entry["key"] for entry in updated_genesis["abci_genesis"]["genesis"]
    ]

    # Check that old approval was removed
    assert "con_token1.balances:wallet1:wallet2" not in keys

    # Check that new approval was added
    assert "con_token1.approvals:wallet1:wallet2" in keys

    # Check that new approval was added
    assert "currency.approvals:wallet1:wallet2" in keys

    # Check that regular balance entry was preserved
    assert "con_token1.balances:wallet3" in keys

    # Check that pixel token entries were preserved
    assert "con_pixel_token.balances:wallet1:wallet2" in keys


def test_process_genesis_data(sample_token_genesis):
    updated_genesis, changes_made = process_genesis_data(sample_token_genesis)

    assert changes_made == True

    # Verify the same conditions as in test_migrate_approvals
    keys = [
        entry["key"] for entry in updated_genesis["abci_genesis"]["genesis"]
    ]
    assert "con_token1.balances:wallet1:wallet2" not in keys
    assert "con_token1.approvals:wallet1:wallet2" in keys
    assert "con_token1.balances:wallet3" in keys
    assert "con_pixel_token.balances:wallet1:wallet2" in keys


def test_no_changes_needed():
    # Genesis with no XSC001 tokens
    genesis_data = {
        "abci_genesis": {
            "genesis": [
                {"key": "con_other.__code__", "value": "def something(): pass"}
            ]
        }
    }

    updated_genesis, changes_made = process_genesis_data(genesis_data)
    assert changes_made == False
    assert updated_genesis == genesis_data


def test_with_real_genesis(genesis_data):
    """Test with the actual genesis file from fixtures"""
    updated_genesis, changes_made = process_genesis_data(genesis_data)

    if changes_made:
        # If there were XSC001 tokens in the genesis file,
        # verify that their approval entries were properly migrated
        for entry in updated_genesis["abci_genesis"]["genesis"]:
            key = entry["key"]
            # No old-style approvals should exist
            assert not (
                ".balances:" in key
                and key.count(":") == 2
                and "pixel" not in key
            )
