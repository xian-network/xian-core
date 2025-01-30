balances = Hash(default_value=0)
metadata = Hash()
permits = Hash()
streams = Hash()

TransferEvent = LogEvent(
    event="Transfer",
    params={
        "from": {"type": str, "idx": True},
        "to": {"type": str, "idx": True},
        "amount": {"type": (int, float, decimal)},
    },
)
ApproveEvent = LogEvent(
    event="Approve",
    params={
        "from": {"type": str, "idx": True},
        "to": {"type": str, "idx": True},
        "amount": {"type": (int, float, decimal)},
    },
)
StreamCreatedEvent = LogEvent(
    event="StreamCreated",
    params={
        "sender": {"type": str, "idx": True},
        "receiver": {"type": str, "idx": True},
        "stream_id": {"type": str, "idx": True},
        "rate": {"type": (int, float, decimal)},
        "begins": {"type": str},
        "closes": {"type": str},
    },
)
StreamBalanceEvent = LogEvent(
    event="StreamBalance",
    params={
        "receiver": {"type": str, "idx": True},
        "sender": {"type": str, "idx": True},
        "stream_id": {"type": str, "idx": True},
        "amount": {"type": (int, float, decimal)},
        "balancer": {"type": str},
    },
)
StreamCloseChangeEvent = LogEvent(
    event="StreamCloseChange",
    params={
        "receiver": {"type": str, "idx": True},
        "sender": {"type": str, "idx": True},
        "stream_id": {"type": str, "idx": True},
        "time": {"type": str},
    },
)
StreamForfeitEvent = LogEvent(
    event="StreamForfeit",
    params={
        "receiver": {"type": str, "idx": True},
        "sender": {"type": str, "idx": True},
        "stream_id": {"type": str, "idx": True},
        "time": {"type": str},
    },
)

StreamFinalizedEvent = LogEvent(
    event="StreamFinalized",
    params={
        "receiver": {"type": str, "idx": True},
        "sender": {"type": str, "idx": True},
        "stream_id": {"type": str, "idx": True},
        "time": {"type": str},
    },
)


@construct
def seed(vk: str):
    balances[vk] = 5555555.55 # 5% Team Tokens
    balances["team_vesting"] = 16666666.65 # 15% Team Tokens 5 Year Release, Directly minted into Lock contract
    balances["dao"] = 10999999.989 # 33% DAO Tokens, Directly minted into DAO contract
    balances["dao_funding_stream"] = 22333333.311 # 67% DAO Tokens, to be streamed over 6 years.
    balances["team_lock"] += 49999999.95 # 45% Second batch of public tokens, to be sent out after mint
    balances[vk] += 5555555.55 # 5% Seed participation tokens
    
    
    metadata["token_name"] = "XIAN"
    metadata["token_symbol"] = "XIAN"
    metadata["token_logo_url"] = "https://xian.org/assets/img/logo.svg"
    metadata["token_website"] = "https://xian.org"
    metadata["operator"] = "team_lock"

    # TEAM LOCK
    # 365 * 4 + 364 = 1824 (4 years + 1 leap-year)
    # 1824 * 24 * 60 * 60 = 157593600 (seconds in duration)
    # 16666666.65 / 157593600 (release per second)
    
    # Leaving this in for reference, even though stream was remove for rcnet
    setup_seed_stream(stream_id="team_vesting", sender="team_vesting", receiver="team_lock", rate=0.10575725568804825, duration_days=1824)

    # DAO FUNDING STREAM
    # 365 * 5 + 364 = 2189 (5 years + 1 leap-year)
    # 2189 * 24 * 60 * 60 = 189129600 (seconds in duration)
    # 22333333.311 / 189129600 = 0.1180848122715852 (release per second)
    
    setup_seed_stream(stream_id="dao_funding_stream", sender="dao_funding_stream", receiver="dao", rate=0.1180848122715852, duration_days=2189)

def setup_seed_stream(stream_id: str, sender: str, receiver: str, rate: float, duration_days: int):
    streams[stream_id, 'status'] = "active"
    streams[stream_id, 'begins'] = now
    streams[stream_id, 'closes'] = now + datetime.timedelta(days=duration_days)
    streams[stream_id, 'receiver'] = receiver
    streams[stream_id, 'sender'] = sender
    streams[stream_id, 'rate'] = rate
    streams[stream_id, 'claimed'] = 0
    

@export
def change_metadata(key: str, value: Any):
    assert ctx.caller == metadata["operator"], "Only operator can set metadata."
    metadata[key] = value


@export
def transfer(amount: float, to: str):
    assert amount > 0, 'Cannot send negative balances.'
    assert balances[ctx.caller] >= amount, 'Not enough coins to send.'

    balances[ctx.caller] -= amount
    balances[to] += amount
    
    TransferEvent({"from":ctx.caller, "to":to, "amount":amount})


@export
def approve(amount: float, to: str):
    assert amount >= 0, 'Cannot approve negative balances.'
    balances[ctx.caller, to] = amount
    ApproveEvent({"from":ctx.caller, "to":to, "amount":amount})


@export
def transfer_from(amount: float, to: str, main_account: str):
    assert amount > 0, 'Cannot send negative balances.'
    assert balances[main_account, ctx.caller] >= amount, f'Not enough coins approved to send. You have {balances[main_account, ctx.caller]} approved and are trying to spend {amount}'
    assert balances[main_account] >= amount, 'Not enough coins to send.'
    

    balances[main_account, ctx.caller] -= amount
    balances[main_account] -= amount
    balances[to] += amount

    TransferEvent({"from":main_account, "to":to, "amount":amount})

@export 
def balance_of(address: str):
    return balances[address]


# XSC002 / Permit

@export
def permit(owner: str, spender: str, value: float, deadline: str, signature: str):
    deadline = strptime_ymdhms(deadline)
    permit_msg = construct_permit_msg(owner, spender, value, str(deadline))
    permit_hash = hashlib.sha3(permit_msg)

    assert permits[permit_hash] is None, 'Permit can only be used once.'
    assert now < deadline, 'Permit has expired.'
    assert value >= 0, 'Cannot approve negative balances!'
    assert crypto.verify(owner, permit_msg, signature), 'Invalid signature.'
    
    balances[owner, spender] = value
    permits[permit_hash] = True

    ApproveEvent({"from":owner, "to":spender, "amount":value})
    
    return permit_hash


def construct_permit_msg(owner: str, spender: str, value: float, deadline: str):
    return f"{owner}:{spender}:{value}:{deadline}:{ctx.this}:{chain_id}"


# XSC003 / Streaming Payments


SENDER_KEY = "sender"
RECEIVER_KEY = "receiver"
STATUS_KEY = "status"
BEGIN_KEY = "begins"
CLOSE_KEY = "closes"
RATE_KEY = "rate"
CLAIMED_KEY = "claimed"
STREAM_ACTIVE = "active"
STREAM_FINALIZED = "finalized"
STREAM_FORFEIT = "forfeit"


# Creates a new stream to a receiver from ctx.caller
# Stream can begin at any point in past / present / future
# Wrapper for perform_create_stream
@export
def create_stream(receiver: str, rate: float, begins: str, closes: str):
    begins = strptime_ymdhms(begins)
    closes = strptime_ymdhms(closes)
    sender = ctx.caller

    stream_id = perform_create_stream(sender, receiver, rate, begins, closes)
    return stream_id


# Internal function used to create a stream from a permit or from a direct call from the sender
def perform_create_stream(sender: str, receiver: str, rate: float, begins: str, closes: str):
    stream_id = hashlib.sha3(f"{sender}:{receiver}:{begins}:{closes}:{rate}")
    
    assert streams[stream_id, STATUS_KEY] is None, 'Stream already exists.'
    assert begins < closes, 'Stream cannot begin after the close date.'
    assert rate > 0, 'Rate must be greater than 0.'

    streams[stream_id, STATUS_KEY] = STREAM_ACTIVE
    streams[stream_id, BEGIN_KEY] = begins
    streams[stream_id, CLOSE_KEY] = closes
    streams[stream_id, RECEIVER_KEY] = receiver
    streams[stream_id, SENDER_KEY] = sender
    streams[stream_id, RATE_KEY] = rate
    streams[stream_id, CLAIMED_KEY] = 0

    StreamCreatedEvent({"sender":sender, "receiver":receiver, "stream_id":stream_id, "rate":rate, "begins":str(begins), "closes":str(closes)})

    return stream_id


# Creates a payment stream from a valid signature of a permit message
# Wrapper for perform_create_stream
@export
def create_stream_from_permit(sender: str, receiver: str, rate: float, begins: str, closes: str, deadline: str, signature: str):
    begins = strptime_ymdhms(begins)
    closes = strptime_ymdhms(closes)
    deadline = strptime_ymdhms(deadline)

    assert now < deadline, 'Permit has expired.'
    permit_msg = construct_stream_permit_msg(sender, receiver, rate, begins, closes, deadline)
    permit_hash = hashlib.sha3(permit_msg)

    assert permits[permit_hash] is None, 'Permit can only be used once.'
    assert crypto.verify(sender, permit_msg, signature), 'Invalid signature.'

    permits[permit_hash] = True

    return perform_create_stream(sender, receiver, rate, begins, closes)


# Moves balance due from stream from sender to receiver.
# Called by `sender` or `receiver`
@export
def balance_stream(stream_id: str):
    assert streams[stream_id, STATUS_KEY], 'Stream does not exist.'
    assert streams[stream_id, STATUS_KEY] == STREAM_ACTIVE, 'You can only balance active streams.'
    assert now > streams[stream_id, BEGIN_KEY], 'Stream has not started yet.'

    sender = streams[stream_id, SENDER_KEY]
    receiver = streams[stream_id, RECEIVER_KEY]

    assert ctx.caller in [sender, receiver], 'Only sender or receiver can balance a stream.'

    closes = streams[stream_id, CLOSE_KEY]
    begins = streams[stream_id, BEGIN_KEY]
    rate = streams[stream_id, RATE_KEY]
    claimed = streams[stream_id, CLAIMED_KEY]

    # Calculate the amount of tokens that can be claimed
    
    outstanding_balance = calc_outstanding_balance(begins, closes, rate, claimed)
    
    assert outstanding_balance > 0, 'No amount due on this stream.'

    claimable_amount = calc_claimable_amount(outstanding_balance, sender)

    balances[sender] -= claimable_amount
    balances[receiver] += claimable_amount

    streams[stream_id, CLAIMED_KEY] += claimable_amount
    
    StreamBalanceEvent({"receiver":receiver, "sender":sender, "stream_id":stream_id, "amount":claimable_amount, "balancer":ctx.caller})



# Sets a stream to expire at some point greater than or equal to the current time.
# If the new closes time is in the past, the stream is closed immediately
# If the new close time < begins, the stream is closed at begin time <invalidated>
# Called by `sender`
@export
def change_close_time(stream_id: str, new_close_time: str):
    new_close_time = strptime_ymdhms(new_close_time)

    assert streams[stream_id, STATUS_KEY], "Stream does not exist."
    assert streams[stream_id, STATUS_KEY] == STREAM_ACTIVE, "Stream is not active."

    sender = streams[stream_id, SENDER_KEY]
    receiver = streams[stream_id, RECEIVER_KEY]
    begins = streams[stream_id, BEGIN_KEY]

    assert ctx.caller == sender, "Only sender can change the close time of a stream."

    # If new close time is in the past or before begin time, close immediately or at begin time
    if new_close_time <= now:
        streams[stream_id, CLOSE_KEY] = now
    elif new_close_time < begins:
        streams[stream_id, CLOSE_KEY] = begins
    else:
        streams[stream_id, CLOSE_KEY] = new_close_time

    StreamCloseChangeEvent(
        {
            "receiver": receiver,
            "sender": sender,
            "stream_id": stream_id,
            "time": str(streams[stream_id, CLOSE_KEY]),
        }
    )

# Set the stream inactive.
# A stream must be balanced before it can be finalized.
# Closes must be <= now
# Once a stream is finalized, it cannot be re-opened.
# Called by : `sender` or `receiver`
@export
def finalize_stream(stream_id: str):
    assert streams[stream_id, STATUS_KEY], 'Stream does not exist.'
    assert streams[stream_id, STATUS_KEY] == STREAM_ACTIVE, 'Stream is not active.'

    sender = streams[stream_id, "sender"]
    receiver = streams[stream_id, "receiver"]

    assert ctx.caller in [sender, receiver], 'Only sender or receiver can finalize a stream.'

    begins = streams[stream_id, BEGIN_KEY]
    closes = streams[stream_id, CLOSE_KEY]
    rate = streams[stream_id, RATE_KEY]
    claimed = streams[stream_id, CLAIMED_KEY]

    assert closes <= now, 'Stream has not closed yet.'

    outstanding_balance = calc_outstanding_balance(begins, closes, rate, claimed)

    assert outstanding_balance == 0, 'Stream has outstanding balance.'

    streams[stream_id, STATUS_KEY] = STREAM_FINALIZED
    
    StreamFinalizedEvent({"receiver":receiver, "sender":sender, "stream_id":stream_id, "time":str(now)})



# Convenience method to close a stream, balance it and finalize it
# Called by `sender`
@export
def close_balance_finalize(stream_id: str):
    change_close_time(stream_id=stream_id, new_close_time=str(now))
    balance_finalize(stream_id=stream_id)


# Convenience method to balance a stream and finalize it
# Called by `receiver` or `sender`
@export
def balance_finalize(stream_id: str):
    balance_stream(stream_id=stream_id)
    finalize_stream(stream_id=stream_id)


# Forfeit a stream to the sender
# Called by `receiver`
@export
def forfeit_stream(stream_id: str) -> str:
    assert streams[stream_id, STATUS_KEY], 'Stream does not exist.'
    assert streams[stream_id, STATUS_KEY] == STREAM_ACTIVE, 'Stream is not active.'

    receiver = streams[stream_id, RECEIVER_KEY]
    sender = streams[stream_id, SENDER_KEY]

    assert ctx.caller == receiver, 'Only receiver can forfeit a stream.'

    streams[stream_id, STATUS_KEY] = STREAM_FORFEIT
    streams[stream_id, CLOSE_KEY] = now
    
    StreamForfeitEvent({"receiver":receiver, "sender":sender, "stream_id":stream_id, "time":str(now)})



def calc_outstanding_balance(begins: datetime.datetime, closes: datetime.datetime, rate: float, claimed: float) -> float:
    claimable_end_point = now if now < closes else closes
    claimable_period = claimable_end_point - begins
    claimable_seconds = claimable_period.seconds
    amount_due = (rate * claimable_seconds) - claimed
    return amount_due


def calc_claimable_amount(amount_due: float, sender:str) -> float:
    return amount_due if amount_due < balances[sender] else balances[sender]


def construct_stream_permit_msg(sender:str, receiver:str, rate:float, begins:str, closes:str, deadline:str) -> str:
    return f"{sender}:{receiver}:{rate}:{begins}:{closes}:{deadline}:{ctx.this}:{chain_id}"


def strptime_ymdhms(date_string: str) -> datetime.datetime:
    return datetime.datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
