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
def submit_transaction(contract: str = None, function: str = None, args: dict = None, tx_type: str = 'external'):
    """
    Submits a new transaction to the multisig wallet.
    - contract: Target contract name to call
    - function: Function name to call on the target contract
    - args: Dictionary of arguments to pass to the function
    - tx_type: Type of transaction ('external', 'addOwner', 'removeOwner', 'changeRequirement')
    """
    assert owners[ctx.caller], 'Only owners can submit transactions.'
    args = args or {}

    # Validate based on transaction type
    if tx_type == 'external':
        assert contract is not None, 'Contract name must be specified'
        assert function is not None, 'Function name must be specified'
    elif tx_type == 'addOwner':
        assert 'address' in args, 'Owner address must be specified'
    elif tx_type == 'removeOwner':
        assert 'address' in args, 'Owner address must be specified'
    elif tx_type == 'changeRequirement':
        assert 'required' in args, 'Required signatures must be specified'
    else:
        raise Exception('Invalid transaction type')

    tx_id = transaction_count.get() + 1
    transaction_count.set(tx_id)

    transactions[tx_id, 'type'] = tx_type
    transactions[tx_id, 'contract'] = contract
    transactions[tx_id, 'function'] = function
    transactions[tx_id, 'args'] = args
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
    args = transactions[tx_id, 'args']

    if tx_type == 'external':
        contract_name = transactions[tx_id, 'contract']
        function_name = transactions[tx_id, 'function']
        
        res = importlib.call_function(contract_name, 'export_test', {})
        return res
    elif tx_type == 'addOwner':
        address = args['address']
        assert not owners[address], 'Address is already an owner'
        owners[address] = True
        owner_count.set(owner_count.get() + 1)
    
    elif tx_type == 'removeOwner':
        address = args['address']
        assert owners[address], 'Address is not an owner'
        assert owner_count.get() > required_signatures.get(), 'Cannot remove owner: would make approvals impossible'
        owners[address] = False
        owner_count.set(owner_count.get() - 1)
    
    elif tx_type == 'changeRequirement':
        new_required = args['required']
        assert new_required > 0, 'Required signatures must be greater than 0'
        assert new_required <= owner_count.get(), 'Required signatures cannot exceed owner count'
        required_signatures.set(new_required)

    transactions[tx_id, 'executed'] = True

    return f"Transaction {tx_id} executed."


@export
def balance_stream():
    """
    Executes balance_stream function from currency 
    contract which sends tokens to this contract
    """
    currency.balance_stream(stream_id.get())