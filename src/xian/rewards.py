import decimal

import xian.constants as c

from collections import defaultdict


def calculate_participant_reward(
        participant_ratio, number_of_participants, total_stamps_to_split
    ):
        number_of_participants = (
            number_of_participants if number_of_participants != 0 else 1
        )
        reward = (
            decimal.Decimal(str(participant_ratio)) / number_of_participants
        ) * decimal.Decimal(str(total_stamps_to_split))
        rounded_reward = round(reward, c.DUST_EXPONENT)
        return rounded_reward


def find_developer_and_reward(
        total_stamps_to_split, contract: str, developer_ratio, client
    ):
        # Find all transactions and the developer of the contract.
        # Count all stamps used by people and multiply it by the developer ratio
        send_map = defaultdict(lambda: 0)

        recipient = client.get_var(contract=contract, variable="__developer__")

        send_map[recipient] += total_stamps_to_split * developer_ratio
        send_map[recipient] /= len(send_map)

        return send_map


def calculate_tx_output_rewards(
        total_stamps_to_split, contract, client
    ):
        try:
            (
                master_ratio,
                burn_ratio,
                foundation_ratio,
                developer_ratio,
            ) = client.get_var(contract="rewards", variable="S", arguments=["value"])
        except TypeError:
            raise NotImplementedError(
                "Driver could not get value for key rewards.S:value. Try setting up rewards."
            )

        master_reward = calculate_participant_reward(
            participant_ratio=master_ratio,
            number_of_participants=len(
                client.get_var(
                    contract="masternodes", variable="S", arguments=["members"]
                )
            ),
            total_stamps_to_split=total_stamps_to_split,
        )

        foundation_reward = calculate_participant_reward(
            participant_ratio=foundation_ratio,
            number_of_participants=1,
            total_stamps_to_split=total_stamps_to_split,
        )

        developer_mapping = find_developer_and_reward(
            total_stamps_to_split=total_stamps_to_split,
            contract=contract,
            client=client,
            developer_ratio=developer_ratio,
        )

        return master_reward, foundation_reward, developer_mapping


def distribute_rewards(stamp_rewards_amount, stamp_rewards_contract, driver, client):
    if stamp_rewards_amount > 0:
        (
            master_reward,
            foundation_reward,
            developer_mapping,
        ) = calculate_tx_output_rewards(
            total_stamps_to_split=stamp_rewards_amount,
            contract=stamp_rewards_contract,
            client=client,
        )

        stamp_cost = driver.get("stamp_cost.S:value")

        master_reward /= stamp_cost
        foundation_reward /= stamp_cost

        rewards = []

        for m in driver.get("masternodes.S:members"):
            m_balance = driver.get(f"currency.balances:{m}") or 0
            m_balance_after = round((m_balance + master_reward), c.DUST_EXPONENT)
            rewards.append(
                driver.set(f"currency.balances:{m}", m_balance_after)
            )

        foundation_wallet = driver.get("foundation.owner")
        foundation_balance = driver.get(f"currency.balances:{foundation_wallet}") or 0
        foundation_balance_after = round((foundation_balance + foundation_reward), c.DUST_EXPONENT)
        rewards.append(
            driver.set(f"currency.balances:{foundation_wallet}", foundation_balance_after)
        )

        # Send rewards to each developer calculated from the block
        for recipient, amount in developer_mapping.items():
            # That is genesis contracts or the submission contract
            if recipient == "sys" or recipient is None:
                recipient = driver.get("foundation.owner")
            dev_reward = round((amount / stamp_cost), c.DUST_EXPONENT)
            recipient_balance = driver.get(f"currency.balances:{recipient}") or 0
            recipient_balance_after = round((recipient_balance + dev_reward), c.DUST_EXPONENT)
            rewards.append(
                driver.set(f"currency.balances:{recipient}", recipient_balance_after)
            )

    return rewards


def distribute_static_rewards(driver, master_reward=None, foundation_reward=None):
    rewards = []

    for m in driver.get("masternodes.S:members"):
        m_balance = driver.get(f"currency.balances:{m}") or 0
        m_balance_after = round((m_balance + master_reward), c.DUST_EXPONENT)
        rewards.append(
            driver.set(f"currency.balances:{m}", m_balance_after)
        )

    foundation_wallet = driver.get("foundation.owner")
    foundation_balance = driver.get(f"currency.balances:{foundation_wallet}") or 0
    foundation_balance_after = round((foundation_balance + foundation_reward), c.DUST_EXPONENT)
    rewards.append(
        driver.set(f"currency.balances:{foundation_wallet}", foundation_balance_after)
    )

    return rewards
