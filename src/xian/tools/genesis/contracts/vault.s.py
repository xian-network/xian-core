owners = Hash()
required_signatures = Variable()
owner_count = Variable()
transaction_count = Variable()
stream_id = Variable()
transactions = Hash()


"""
VARS : 
{
    '__name__': 'currency',
    '__doc__': None,
    '__package__': '',
    '__loader__': <contracting.execution.module.DatabaseLoader object at 0xffff80027950>,
    '__spec__': ModuleSpec(name='currency', loader=<contracting.execution.module.DatabaseLoader object at 0xffff80027950>),
    'Variable': <class 'contracting.stdlib.bridge.orm.V'>,
    'Hash': <class 'contracting.stdlib.bridge.orm.H'>,
    'ForeignVariable': <class 'contracting.stdlib.bridge.orm.FV'>,
    'ForeignHash': <class 'contracting.stdlib.bridge.orm.FH'>,
    'LogEvent': <class 'contracting.stdlib.bridge.orm.LE'>,
    '__Contract': <class 'contracting.stdlib.bridge.orm.C'>,
    'hashlib': <module 'hashlib'>,
    'datetime': <module 'datetime'>,
    'random': <module 'random'>,
    'importlib': <module 'importlib'>,
    '__export': <class 'contracting.stdlib.bridge.access.__export'>,
    'ctx': <contracting.execution.runtime.Context object at 0xffff96de05d0>,
    'rt': <contracting.execution.runtime.Runtime object at 0xffff96de2d50>,
    'Any': typing.Any,
    'decimal': <class 'contracting.stdlib.bridge.decimal.ContractingDecimal'>,
    'crypto': <module 'crypto'>,
    '__Driver': <contracting.storage.driver.Driver object at 0xffff7ff93310>,
    'chain_id': 'test-chain',
    'now': 2025-01-08 15:50:00,
    '__contract__': True,
    '__balances': <contracting.stdlib.bridge.orm.H object at 0xffff80026b50>,
    '__metadata': <contracting.stdlib.bridge.orm.H object at 0xffff80027710>,
    '__permits': <contracting.stdlib.bridge.orm.H object at 0xffff80024a10>,
    '__streams': <contracting.stdlib.bridge.orm.H object at 0xffff80025e10>,
    '__TransferEvent': <contracting.stdlib.bridge.orm.LE object at 0xffff800240d0>,
    '__ApproveEvent': <contracting.stdlib.bridge.orm.LE object at 0xffff80024990>,
    '__StreamCreatedEvent': <contracting.stdlib.bridge.orm.LE object at 0xffff96fcb210>,
    '__StreamBalanceEvent': <contracting.stdlib.bridge.orm.LE object at 0xffff96f74f10>,
    '__StreamCloseChangeEvent': <contracting.stdlib.bridge.orm.LE object at 0xffff96fc69d0>,
    '__StreamForfeitEvent': <contracting.stdlib.bridge.orm.LE object at 0xffff96fc6610>,
    '__StreamFinalizedEvent': <contracting.stdlib.bridge.orm.LE object at 0xffff7ffae610>,
    '____': <function ____ at 0xffff7ffc31a0>,
    '__setup_seed_stream': <function __setup_seed_stream at 0xffff7ffc32e0>,
    'change_metadata': <function change_metadata at 0xffff7ffc3420>,
    'transfer': <function transfer at 0xffff7ffc3560>,
    'approve': <function approve at 0xffff7ffc36a0>,
    'transfer_from': <function transfer_from at 0xffff7ffc37e0>,
    'balance_of': <function balance_of at 0xffff7ffc3920>,
    'permit': <function permit at 0xffff7ffc3a60>,
    '__construct_permit_msg': <function __construct_permit_msg at 0xffff7ffc3b00>,
    'SENDER_KEY': 'sender',
    'RECEIVER_KEY': 'receiver',
    'STATUS_KEY': 'status',
    'BEGIN_KEY': 'begins',
    'CLOSE_KEY': 'closes',
    'RATE_KEY': 'rate',
    'CLAIMED_KEY': 'claimed',
    'STREAM_ACTIVE': 'active',
    'STREAM_FINALIZED': 'finalized',
    'STREAM_FORFEIT': 'forfeit',
    'create_stream': <function create_stream at 0xffff7ffc3c40>,
    '__perform_create_stream': <function __perform_create_stream at 0xffff7ffc3ce0>,
    'create_stream_from_permit': <function create_stream_from_permit at 0xffff7ffc3e20>,
    'balance_stream': <function balance_stream at 0xffff7ffc3f60>,
    'change_close_time': <function change_close_time at 0xffff7fff80e0>,
    'finalize_stream': <function finalize_stream at 0xffff7fff8220>,
    'close_balance_finalize': <function close_balance_finalize at 0xffff7fff8360>,
    'balance_finalize': <function balance_finalize at 0xffff7fff84a0>,
    'forfeit_stream': <function forfeit_stream at 0xffff7fff85e0>,
    '__calc_outstanding_balance': <function __calc_outstanding_balance at 0xffff7fff8680>,
    '__calc_claimable_amount': <function __calc_claimable_amount at 0xffff7fff8720>,
    '__construct_stream_permit_msg': <function __construct_stream_permit_msg at 0xffff7fff87c0>,
    '__strptime_ymdhms': <function __strptime_ymdhms at 0xffff7fff8860>
}
"""


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
