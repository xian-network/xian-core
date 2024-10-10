from loguru import logger

# Define a scaling factor for ratios to handle percentages as integers
SCALING_FACTOR = 1_000_000  # Represents 100%


class RewardsHandler:

    def __init__(self, client):
        self.client = client

    def calculate_participant_reward(self, participant_ratio, number_of_participants, total_stamps_to_split):
        """
        Calculates the reward for participants based on their ratio and total stamps to split.
        """
        number_of_participants = number_of_participants if number_of_participants != 0 else 1
        try:
            if isinstance(participant_ratio, dict):
                participant_ratio = int(participant_ratio.get("__big_int__", 0))
            else:
                participant_ratio = int(participant_ratio)

            # Calculate reward using integer arithmetic
            reward = (participant_ratio * total_stamps_to_split) // (number_of_participants * SCALING_FACTOR)
        except Exception as e:
            logger.error(f"Error in calculating reward: {e}")
            reward = 0
        return reward  # Return integer reward

    def find_developer_and_reward(self, total_stamps_to_split, contract, developer_ratio):
        """
        Determines the developer's reward and returns a mapping of developer addresses to rewards.
        """
        if isinstance(developer_ratio, dict):
            developer_ratio = int(developer_ratio.get("__big_int__", 0))
        else:
            developer_ratio = int(developer_ratio)

        recipient = self.client.get_var(contract=contract, variable="__developer__")
        if not recipient:
            recipient = self.client.get_var(contract="foundation", variable="owner")

        reward = (developer_ratio * total_stamps_to_split) // SCALING_FACTOR
        return {recipient: reward}

    def calculate_tx_output_rewards(self, total_stamps_to_split, contract):
        """
        Calculates the rewards for masternodes, foundation, and developers based on the total stamps used.
        """
        rewards_setup = self.client.get_var(contract="rewards", variable="S", arguments=["value"])
        if not rewards_setup:
            logger.error("Rewards not set up.")
            return 0, 0, {}
        try:
            master_ratio, burn_ratio, foundation_ratio, developer_ratio = rewards_setup
        except TypeError:
            raise NotImplementedError("Driver could not get value for key rewards.S:value. Try setting up rewards.")

        # Convert ratios to integers
        master_ratio = int(master_ratio)
        foundation_ratio = int(foundation_ratio)
        developer_ratio = int(developer_ratio)
        burn_ratio = int(burn_ratio)

        # Verify that the total ratio sums up to the scaling factor
        total_ratio = master_ratio + burn_ratio + foundation_ratio + developer_ratio
        if total_ratio != SCALING_FACTOR:
            logger.warning(f"Total rewards ratio {total_ratio} does not equal SCALING_FACTOR {SCALING_FACTOR}")
            # Adjust ratios or handle the discrepancy as needed

        # Calculate rewards
        num_masternodes = len(self.client.get_var(contract="masternodes", variable="nodes") or [])
        master_reward = self.calculate_participant_reward(
            participant_ratio=master_ratio,
            number_of_participants=num_masternodes,
            total_stamps_to_split=total_stamps_to_split
        )

        foundation_reward = self.calculate_participant_reward(
            participant_ratio=foundation_ratio,
            number_of_participants=1,
            total_stamps_to_split=total_stamps_to_split
        )

        developer_mapping = self.find_developer_and_reward(
            total_stamps_to_split=total_stamps_to_split,
            contract=contract,
            developer_ratio=developer_ratio
        )

        return master_reward, foundation_reward, developer_mapping

    def distribute_rewards(self, stamp_rewards_amount, stamp_rewards_contract):
        """
        Distributes the rewards to masternodes, foundation, and developers based on the stamps used.
        """
        if not self.client.get_var(contract="rewards", variable="S", arguments=["value"]) or stamp_rewards_amount <= 0:
            return []

        driver = self.client.raw_driver
        master_reward, foundation_reward, developer_mapping = self.calculate_tx_output_rewards(
            total_stamps_to_split=stamp_rewards_amount,
            contract=stamp_rewards_contract
        )

        stamp_cost = driver.get("stamp_cost.S:value")
        if stamp_cost is None or stamp_cost == 0:
            stamp_cost = 1  # Avoid division by zero
        else:
            stamp_cost = int(stamp_cost)

        # Convert rewards from stamps to minimal currency units
        master_reward = master_reward // stamp_cost
        foundation_reward = foundation_reward // stamp_cost

        rewards = []
        rewards.extend(self._distribute_masternode_rewards(driver, master_reward))
        rewards.append(self._distribute_foundation_reward(driver, foundation_reward))
        rewards.extend(self._distribute_developer_rewards(driver, developer_mapping, stamp_cost))

        return rewards

    def _distribute_masternode_rewards(self, driver, master_reward_total):
        """
        Distributes the master reward among masternodes.
        """
        rewards = []
        masternodes = driver.get("masternodes.nodes") or []
        num_masternodes = len(masternodes)
        if num_masternodes == 0 or master_reward_total == 0:
            return rewards  # No masternodes or no reward to distribute

        reward_per_node = master_reward_total // num_masternodes
        remainder = master_reward_total % num_masternodes  # Handle any remainder

        for i, m in enumerate(masternodes):
            m_balance = driver.get(f"currency.balances:{m}") or 0
            # Distribute remainder to the first few masternodes
            extra = 1 if i < remainder else 0
            m_balance_after = m_balance + reward_per_node + extra
            driver.set(f"currency.balances:{m}", m_balance_after)
            rewards.append({'address': m, 'amount': reward_per_node + extra})
        return rewards

    def _distribute_foundation_reward(self, driver, foundation_reward):
        """
        Distributes the foundation reward.
        """
        foundation_wallet = driver.get("foundation.owner")
        foundation_balance = driver.get(f"currency.balances:{foundation_wallet}") or 0
        foundation_balance_after = foundation_balance + foundation_reward
        driver.set(f"currency.balances:{foundation_wallet}", foundation_balance_after)
        return {'address': foundation_wallet, 'amount': foundation_reward}

    def _distribute_developer_rewards(self, driver, developer_mapping, stamp_cost):
        """
        Distributes the developer rewards.
        """
        rewards = []
        for recipient, amount in developer_mapping.items():
            if recipient == "sys" or recipient is None:
                recipient = driver.get("foundation.owner")
            dev_reward = amount // stamp_cost
            recipient_balance = driver.get(f"currency.balances:{recipient}") or 0
            recipient_balance_after = recipient_balance + dev_reward
            driver.set(f"currency.balances:{recipient}", recipient_balance_after)
            rewards.append({'address': recipient, 'amount': dev_reward})
        return rewards

    def distribute_static_rewards(self, master_reward, foundation_reward):
        """
        Distributes static rewards to masternodes and foundation.
        """
        rewards = []
        driver = self.client.raw_driver

        rewards.extend(self._distribute_masternode_rewards(driver, master_reward))
        rewards.append(self._distribute_foundation_reward(driver, foundation_reward))

        return rewards
