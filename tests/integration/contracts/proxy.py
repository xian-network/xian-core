import currency

def transfer(amount: float, to: str):
    return currency.transfer(amount, to)

@export
def send_multiple(amount: float, to: list):
    for t in to:
        currency.transfer(amount, t)
