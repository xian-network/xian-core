from contracting.db.driver import (
    ContractDriver,
)
from contracting.stdlib.bridge.decimal import ContractingDecimal

LATEST_BLOCK_HASH_KEY = "__latest_block.hash"
LATEST_BLOCK_HEIGHT_KEY = "__latest_block.height"
DUST_EXPONENT = 8

def get_latest_block_hash(driver: ContractDriver):
    latest_hash = driver.get(LATEST_BLOCK_HASH_KEY)
    if latest_hash is None:
        return b""
    return latest_hash


def set_latest_block_hash(h, driver: ContractDriver):
    driver.set(LATEST_BLOCK_HASH_KEY, h)


def get_latest_block_height(driver: ContractDriver):
    h = driver.get(LATEST_BLOCK_HEIGHT_KEY, save=False)
    if h is None:
        return 0

    if type(h) == ContractingDecimal:
        h = int(h._d)

    return int(h)


def set_latest_block_height(h, driver: ContractDriver):
    driver.set(LATEST_BLOCK_HEIGHT_KEY, int(h))


def get_value_of_key(item: str, driver: ContractDriver):
    return driver.get(item)

def distribute_rewards(stamp_rewards_amount, stamp_rewards_contract, reward_manager, driver, client):
    if stamp_rewards_amount > 0:
        (
            master_reward,
            foundation_reward,
            developer_mapping,
        ) = reward_manager.calculate_tx_output_rewards(
            total_stamps_to_split=stamp_rewards_amount,
            contract=stamp_rewards_contract,
            client=client,
        )

        stamp_cost = driver.get("stamp_cost.S:value")

        master_reward /= stamp_cost
        foundation_reward /= stamp_cost

        rewards = []

        for m in driver.get("masternodes.S:members"):
            m_balance = driver.get(f"currency.balances:{m}")
            m_balance_after = m_balance + master_reward
            rewards.append(
                driver.set(f"currency.balances:{m}", m_balance_after)
            )

        foundation_wallet = driver.get("foundation.owner")
        foundation_balance = driver.get(f"currency.balances:{foundation_wallet}")
        foundation_balance_after = foundation_balance + foundation_reward
        rewards.append(
            driver.set(f"currency.balances:{foundation_wallet}", foundation_balance_after)
        )

        # Send rewards to each developer calculated from the block
        for recipient, amount in developer_mapping.items():
            if recipient == "sys":
                recipient = driver.get("foundation.owner")
            dev_reward = round((amount / stamp_cost), DUST_EXPONENT)
            recipient_balance = driver.get(f"currency.balances:{recipient}")
            recipient_balance_after = recipient_balance + dev_reward
            rewards.append(
                driver.set(f"currency.balances:{recipient}", recipient_balance_after)
            )
    return rewards

def distribute_static_rewards(driver, master_reward=None, foundation_reward=None):
    rewards = []
    for m in driver.get("masternodes.S:members"):
        m_balance = driver.get(f"currency.balances:{m}")
        m_balance_after = m_balance + master_reward
        rewards.append(
            driver.set(f"currency.balances:{m}", m_balance_after)
        )

    foundation_wallet = driver.get("foundation.owner")
    foundation_balance = driver.get(f"currency.balances:{foundation_wallet}")
    foundation_balance_after = foundation_balance + foundation_reward
    rewards.append(
        driver.set(f"currency.balances:{foundation_wallet}", foundation_balance_after)
    )
    return rewards