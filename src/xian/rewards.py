from contracting.stdlib.bridge.decimal import ContractingDecimal
import decimal
from xian.constants import Constants as c
from collections import defaultdict
from loguru import logger


class RewardsHandler:
    
    def __init__(self, client):
        self.client = client
    
    def calculate_participant_reward(self, participant_ratio, number_of_participants, total_stamps_to_split):
        number_of_participants = number_of_participants if number_of_participants != 0 else 1
        try:
            if isinstance(participant_ratio, dict):
                participant_ratio = participant_ratio["__fixed__"]
            reward = (decimal.Decimal(str(participant_ratio)) / number_of_participants) * decimal.Decimal(str(total_stamps_to_split))
            rounded_reward = round(reward, c.DUST_EXPONENT)
        except Exception as e:
            logger.error(f"Error in calculating reward: {e}")
            rounded_reward = 0
        return ContractingDecimal(str(rounded_reward))
    
    def find_developer_and_reward(self, total_stamps_to_split, contract, developer_ratio):
        if isinstance(developer_ratio, dict):
            developer_ratio = developer_ratio["__fixed__"]
        if not isinstance(developer_ratio, decimal.Decimal):
            developer_ratio = decimal.Decimal(str(developer_ratio))
        
        send_map = defaultdict(lambda: 0)
        recipient = self.client.get_var(contract=contract, variable="__developer__")
        if not recipient:
            return {self.client.get_var(contract="foundation", variable="owner"): ContractingDecimal(str(total_stamps_to_split * developer_ratio))}
        send_map[recipient] += ContractingDecimal(str(total_stamps_to_split * developer_ratio))
        send_map[recipient] /= len(send_map)
        return dict(send_map)
    
    def calculate_tx_output_rewards(self, total_stamps_to_split, contract):
        if not self.client.get_var(contract="rewards", variable="S", arguments=["value"]):
            logger.error("Rewards not set up.")
            return 0, 0, {}
        try:
            master_ratio, burn_ratio, foundation_ratio, developer_ratio = self.client.get_var(contract="rewards", variable="S", arguments=["value"])
        except TypeError:
            raise NotImplementedError("Driver could not get value for key rewards.S:value. Try setting up rewards.")
        
        master_reward = self.calculate_participant_reward(
            participant_ratio=master_ratio,
            number_of_participants=len(self.client.get_var(contract="masternodes", variable="nodes")),
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
        if not self.client.get_var(contract="rewards", variable="S", arguments=["value"]) or stamp_rewards_amount <= 0:
            return []
        
        driver = self.client.raw_driver
        master_reward, foundation_reward, developer_mapping = self.calculate_tx_output_rewards(
            total_stamps_to_split=stamp_rewards_amount,
            contract=stamp_rewards_contract
        )
        
        stamp_cost = driver.get("stamp_cost.S:value")
        master_reward /= stamp_cost
        foundation_reward /= stamp_cost
        
        rewards = self._distribute_masternode_rewards(driver, master_reward)
        rewards.append(self._distribute_foundation_reward(driver, foundation_reward))
        rewards.extend(self._distribute_developer_rewards(driver, developer_mapping, stamp_cost))
        
        return rewards
    
    def _distribute_masternode_rewards(self, driver, master_reward):
        rewards = []
        for m in driver.get("masternodes.nodes"):
            m_balance = driver.get(f"currency.balances:{m}") or 0
            m_balance_after = round(m_balance + master_reward, c.DUST_EXPONENT)
            rewards.append(driver.set(f"currency.balances:{m}", m_balance_after))
        return rewards
    
    def _distribute_foundation_reward(self, driver, foundation_reward):
        foundation_wallet = driver.get("foundation.owner")
        foundation_balance = driver.get(f"currency.balances:{foundation_wallet}") or 0
        foundation_balance_after = round(foundation_balance + foundation_reward, c.DUST_EXPONENT)
        return driver.set(f"currency.balances:{foundation_wallet}", foundation_balance_after)
    
    def _distribute_developer_rewards(self, driver, developer_mapping, stamp_cost):
        rewards = []
        for recipient, amount in developer_mapping.items():
            if recipient == "sys" or recipient is None:
                recipient = driver.get("foundation.owner")
            dev_reward = round(amount / stamp_cost, c.DUST_EXPONENT)
            recipient_balance = driver.get(f"currency.balances:{recipient}") or 0
            recipient_balance_after = round(recipient_balance + dev_reward, c.DUST_EXPONENT)
            rewards.append(driver.set(f"currency.balances:{recipient}", recipient_balance_after))
        return rewards
    
    def distribute_static_rewards(self, master_reward, foundation_reward):
        rewards = []
        driver = self.client.raw_driver
        
        rewards.extend(self._distribute_masternode_rewards(driver, master_reward))
        rewards.append(self._distribute_foundation_reward(driver, foundation_reward))
        
        return rewards
