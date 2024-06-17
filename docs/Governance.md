# Governance on Xian Network

Governance is a key component of the Xian Network. It is the process by which the network is managed and decisions are made. The governance process is designed to ensure that the network is secure, stable, and scalable. It is also designed to ensure that the network is able to adapt to changing conditions and requirements.

## Smart Contracts

The governance process is implemented through a series of smart contracts that are deployed on the Xian Network. These smart contracts are designed to allow validators to propose changes to the network and to vote on those changes, as well as directly interact with the network to enforce those changes.

### Deployed Contracts

The following smart contracts are currently deployed on the Xian Network:

- **masternodes**: This contract is the main governance contract for the Xian Network. It manages the list of validators and is used to propose and vote on changes to the network. It interacts with the other contracts to enforce the decisions that are made through the governance process.
- **dao**: This contract is used to manage the DAO treasury.
- **rewards**: This contract is used to manage the rewards that are distributed to contract developers, validators, foundation, and also for deflationary burn.
- **stamp_cost**: This contract is used to manage the cost of stamps on the network (transaction fees).

## Registration Process

To participate in the governance process, users can register as a validator on the Xian Network, which requires staking a certain amount of XIAN tokens. By registering as a validator candidate, other validators can propose and vote on whether to accept the candidate as a validator. Once a candidate is accepted as a validator, they participate in the blockchain consensus process and can propose and vote on changes to the network.

### Validator Registration

To register as a validator on the Xian Network, users must follow these steps:

1. **Approve Transfer**: Approve the masternodes contract to transfer the registration fee in XIAN tokens on your behalf.
2. **Register**: Call the `register` function on the masternodes contract.
3. **Proposal and Voting**: Wait for other validators to propose and vote on your registration.
4. **Become a Validator**: If your registration is accepted, you will become a validator on the Xian Network.

## Voting Process

The governance process on the Xian Network is based on a voting mechanism. Validators can propose changes to the network and vote on those changes. The changes that receive a majority of votes are implemented on the network.

### Proposal Submission

To propose a change to the network, validators must follow these steps:

1. **Submit Proposal**: Call the `propose_vote` function on the masternodes contract. The proposal must include the following information:
   - **Type of Change**: Specify the type of change being proposed. Available options are: `add_member`, `remove_member`, `change_registration_fee`, `reward_change`, `dao_payout`, `stamp_cost_change`, `change_types`.
   - **Value of Change**: Provide the necessary details for the proposed change:
     - `add_member` and `remove_member`: Include the address of the validator being added or removed as a string.
     - `change_registration_fee`: Include the new registration fee as an integer (e.g., 1000).
     - `reward_change`: Include the new reward distribution as a list (e.g., [0.49, 0.01, 0.01, 0.49]).
     - `dao_payout`: Include the amount of XIAN tokens to be paid out and the address of the recipient as a dictionary (e.g., {"amount": 1000, "to": "receiver_address"}).
     - `stamp_cost_change`: Include the new stamp cost as an integer.
     - `change_types`: Include the new types of changes that can be proposed as a list (e.g., ["add_member", "remove_member", "change_registration_fee", "reward_change", "dao_payout", "stamp_cost_change", "change_types"]).

2. **Voting**: Wait for other validators to vote on the proposal.

### Voting

To vote on a proposal, validators must follow these steps:

1. **Cast Vote**: Call the `vote` function on the masternodes contract with the following parameters:
   - **Proposal ID**: The ID of the proposal being voted on (`proposal_id`).
   - **Vote**: The vote being cast. Available options are: `yes` or `no` (`vote`).

The proposal will be accepted if it receives a majority of `yes` votes from the validators. The proposal will be finalized if at least 50% of the validators have voted on it. The proposal will not be executed if it receives a majority of `no` votes from the validators or if `yes` and `no` votes are equal.