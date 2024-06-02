import currency

@export
def transfer_from_dao(amount: float):
    assert amount > 0, 'Amount must be greater than 0'
    assert ctx.caller == ctx.owner, 'Only the voting contract can transfer from DAO'
    currency.transfer_from(amount, ctx.this, ctx.caller)