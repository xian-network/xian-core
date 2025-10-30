@export
def mutate_then_overdraw(key: str, token: str = "currency_1", to: str = "bob", amount: float = 1):
    m = importlib.import_module("con_mutable_map")
    # assign a new value to ensure a write occurs before failure
    m.nested[key] = {"count": 2, "items": [1, 2]}
    t = importlib.import_module(token)
    # This should fail since this contract has zero balance
    t.transfer(amount=amount, to=to)


