import currency

owners = Hash()
required_signatures = Variable()
owner_count = Variable()
transaction_count = Variable()
stream_id = Variable()
transactions = Hash()

@construct
def seed(initial_owners: str, initial_required_signatures: int, stream: str):
    """
    Initializes the multisig contract.
    - initial_owners: Comma-separated string of owner addresses.
    - initial_required_signatures: Number of required signatures to execute a transaction.
    """
    owner_list = initial_owners.split(',')
    for owner in owner_list:
        owners[owner.strip()] = True

    required_signatures.set(initial_required_signatures)
    owner_count.set(len(owner_list))
    transaction_count.set(0)
    stream_id.set(stream)

@export
def submit_transaction(to: str = None, amount: float = None, tx_type: str = 'transfer'):
    """
    Submits a new transaction to the multisig wallet.
    - to: Recipient address.
    - amount: Amount of tokens to transfer.
    - tx_type: Type of transaction ('transfer', 'addOwner', 'removeOwner', 'changeRequirement').
    """
    assert owners[ctx.caller], 'Only owners can submit transactions.'

    tx_id = transaction_count.get() + 1
    transaction_count.set(tx_id)

    transactions[tx_id, 'type'] = tx_type
    transactions[tx_id, 'to'] = to
    transactions[tx_id, 'amount'] = amount
    transactions[tx_id, 'executed'] = False
    transactions[tx_id, 'approvals'] = 0

    # The submitter approves the transaction by default
    approve_transaction(tx_id)

    return f"Transaction {tx_id} submitted."

@export
def approve_transaction(tx_id: int):
    """
    Approves a pending transaction.
    - tx_id: The ID of the transaction to approve.
    """
    assert owners[ctx.caller], 'Only owners can approve transactions.'
    assert not transactions[tx_id, 'executed'], 'Transaction already executed.'
    assert transactions[tx_id, 'type'] is not None, 'Transaction does not exist.'
    assert not transactions[tx_id, 'approvers', ctx.caller], 'Already approved.'

    transactions[tx_id, 'approvers', ctx.caller] = True
    transactions[tx_id, 'approvals'] += 1

    return f"Transaction {tx_id} approved by {ctx.caller}."

@export
def execute_transaction(tx_id: int):
    """
    Executes a transaction if enough approvals are collected.
    - tx_id: The ID of the transaction to execute.
    """
    assert owners[ctx.caller], 'Only owners can execute transactions.'
    assert not transactions[tx_id, 'executed'], 'Transaction already executed.'
    assert transactions[tx_id, 'type'] is not None, 'Transaction does not exist.'
    approvals = transactions[tx_id, 'approvals']
    required = required_signatures.get()
    assert approvals >= required, 'Not enough approvals.'

    tx_type = transactions[tx_id, 'type']
    to = transactions[tx_id, 'to']
    amount = transactions[tx_id, 'amount']
    
    if tx_type == 'transfer':
        currency.transfer(amount=amount, to=to)
    elif tx_type == 'addOwner':
        assert to is not None, 'No owner specified to add.'
        assert not owners[to], 'Address is already an owner.'
        owners[to] = True
        owner_count.set(owner_count.get() + 1)
    elif tx_type == 'removeOwner':
        assert to is not None, 'No owner specified to remove.'
        assert owners[to], 'Address is not an owner.'
        owners[to] = False
        owner_count.set(owner_count.get() - 1)
        if required_signatures.get() > owner_count.get():
            required_signatures.set(owner_count.get())
    elif tx_type == 'changeRequirement':
        assert amount is not None, 'No new requirement specified.'
        new_requirement = int(amount)
        assert new_requirement > 0, 'Requirement must be greater than zero.'
        total_owners = owner_count.get()
        assert new_requirement <= total_owners, 'Requirement cannot be greater than number of owners.'
        required_signatures.set(new_requirement)
    else:
        return 'Invalid transaction type.'

    transactions[tx_id, 'executed'] = True

    return f"Transaction {tx_id} executed."

@export
def balance_stream():
    """
    Executes balance_stream function from currency 
    contract which sends tokens to this contract
    """
    currency.balance_stream(stream_id.get())

@export
def change_currency_metadata(key: str, value: str):
    """
    Changes the metadata of the currency contract
    """
    assert owners[ctx.caller], 'Only owners can change metadata.'
    currency.change_metadata(key, value)
