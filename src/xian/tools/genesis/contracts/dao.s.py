import currency

@export
def transfer_from_dao(args: dict):
    amount = args.get('amount')
    to = args.get('to')
    assert amount > 0, 'Amount must be greater than 0'
    currency.transfer(amount=amount, to=to)
    

@export
def balance_dao_stream():
    currency.balance_stream(stream_id="dao_funding_stream")
