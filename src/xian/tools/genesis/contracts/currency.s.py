balances = Hash(default_value=0)

@construct
def seed(vk: str):
    balances[vk] = 5555555.55 # 5% Team Tokens
    balances["team_lock"] = 16666666.65 # 15% Team Tokens 5 Year Release, Directly minted into Lock contract
    balances["dao"] = 33333333.3 # 30% DAO Tokens, Directly minted into DAO contract
    balances[vk] += 49999999.95 # Public Sale, to be sent out after mint
    balances[vk] += 5555555.55 # Private Sale, to be sent out after mint

@export
def transfer(amount: float, to: str):
    assert amount > 0, 'Cannot send negative balances!'

    sender = ctx.caller

    assert balances[sender] >= amount, 'Not enough coins to send!'

    balances[sender] -= amount
    balances[to] += amount

@export
def balance_of(account: str):
    return balances[account]

@export
def allowance(owner: str, spender: str):
    return balances[owner, spender]

@export
def approve(amount: float, to: str):
    assert amount > 0, 'Cannot send negative balances!'

    sender = ctx.caller
    balances[sender, to] += amount
    return balances[sender, to]

@export
def transfer_from(amount: float, to: str, main_account: str):
    assert amount > 0, 'Cannot send negative balances!'

    sender = ctx.caller

    assert balances[main_account, sender] >= amount, 'Not enough coins approved to send! You have {} and are trying to spend {}'\
        .format(balances[main_account, sender], amount)
    assert balances[main_account] >= amount, 'Not enough coins to send!'

    balances[main_account, sender] -= amount
    balances[main_account] -= amount

    balances[to] += amount
