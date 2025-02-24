import currency

@export
def transfer_from_dao(args: dict):
    contract_name = args.get('contract_name')
    amount = args.get('amount')
    to = args.get('to')
    
    assert contract_name is not None, 'Contract name is required'
    assert amount > 0, 'Amount must be greater than 0'
    assert to is not None, 'To is required'
    
    contract = importlib.import_module(contract_name)
    contract.transfer(amount=amount, to=to)

@export
def balance_stream(stream_id: str):
    currency.balance_stream(stream_id=stream_id)
    
@export
def create_stream(args: dict):
    receiver = args.get('receiver')
    rate = args.get('rate')
    begins = args.get('begins')
    closes = args.get('closes')
    currency.create_stream(receiver=receiver, rate=rate, begins=begins, closes=closes)

@export
def change_close_time(args: dict):
    stream_id = args.get('stream_id')
    new_close_time = args.get('new_close_time')
    assert stream_id is not None, 'Stream ID is required'
    assert new_close_time is not None, 'New close time is required'
    currency.change_close_time(stream_id=stream_id, new_close_time=new_close_time)

@export
def finalize_stream(args: dict):
    stream_id = args.get('stream_id')
    currency.finalize_stream(stream_id=stream_id)
    
@export
def close_balance_finalize(args: dict):
    stream_id = args.get('stream_id')
    assert stream_id is not None, 'Stream ID is required'
    currency.close_balance_finalize(stream_id=stream_id)
