import currency
import election_house

candidate_state = Hash()
top_candidate = Variable()

no_confidence_state = Hash()
last_candidate = Variable()

to_be_relinquished = Variable()

STAMP_COST = 20
member_cost = Variable()

controller = Variable()


@construct
def seed(policy: str='members', cost: int=500_000):
    controller.set(policy)

    member_cost.set(cost)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # STAKING
@export
def register():
    assert not candidate_state['registered', ctx.caller], 'Already registered.'

    currency.transfer_from(member_cost.get(), ctx.this, ctx.caller)

    candidate_state['registered', ctx.caller] = True
    candidate_state['votes', ctx.caller] = 0

    if top_candidate.get() is None:
        top_candidate.set(ctx.caller)

@export
def unregister():
    mns = election_house.current_value_for_policy(controller.get())
    assert candidate_state['registered', ctx.caller], 'Not registered.'

    assert ctx.caller not in mns, "Can't unstake if in governance."

    currency.transfer(member_cost.get(), ctx.caller)

    candidate_state['registered', ctx.caller] = False
    candidate_state['votes', ctx.caller] = 0


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # VOTE CANDIDATE
@export
def vote_candidate(address: str):
    assert candidate_state['registered', address], 'Candidate not registered.'

    # Determine if caller can vote
    v = candidate_state['last_voted', ctx.caller]
    assert v is None or now - v > datetime.DAYS * 1, 'Voting again too soon.'

    # Deduct small vote fee
    vote_cost = STAMP_COST / election_house.current_value_for_policy('stamp_cost')
    currency.transfer_from(vote_cost, 'blackhole', ctx.caller)

    # Update last voted variable
    candidate_state['last_voted', ctx.caller] = now

    votes = candidate_state['votes', address]

    if votes is None:
        candidate_state['votes', address] = 1
    else:
        candidate_state['votes', address] += 1

    if top_candidate.get() is not None:
        if candidate_state['votes', address] > candidate_state['votes', top_candidate.get()]:
            top_candidate.set(address)


@export
def top_member():
    return top_candidate.get()


@export
def pop_top():
    assert ctx.caller == controller.get(), 'Wrong smart contract caller.'

    top = top_member()

    if top is None:
        return None

    candidate_state.clear('votes')
    top_candidate.set(None)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # VOTE NO CONFIDENCE
@export
def vote_no_confidence(address: str):
    # Determine if caller can vote
    assert address in election_house.current_value_for_policy(controller.get()), \
        'Cannot vote against a non-committee member'

    v = no_confidence_state['last_voted', ctx.caller]
    assert v is None or now - v > datetime.DAYS * 1, 'Voting again too soon.'

    # Deduct small vote fee
    vote_cost = STAMP_COST / election_house.current_value_for_policy('stamp_cost')
    currency.transfer_from(vote_cost, 'blackhole', ctx.caller)

    # Update last voted variable
    no_confidence_state['last_voted', ctx.caller] = now

    if no_confidence_state['votes', address] is None:
        no_confidence_state['votes', address] = 1
    else:
        no_confidence_state['votes', address] += 1

    if last_candidate.get() is None:
        last_candidate.set(address)
    else:
        if no_confidence_state['votes', address] > no_confidence_state['votes', last_candidate.get()]:
            last_candidate.set(address)


@export
def last_member():
    r = to_be_relinquished.get()
    if r is not None:
        return r

    return last_candidate.get()


@export
def pop_last():
    assert ctx.caller == controller.get(), 'Wrong smart contract caller.'

    r = to_be_relinquished.get()

    if r is not None:
        no_confidence_state['votes', r] = 0
        to_be_relinquished.set(None)
    else:
        no_confidence_state.clear('votes')
        candidate_state['registered', last_candidate.get()] = False
        last_candidate.set(None)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # REMOVE!!
@export
def force_removal(address: str):
    assert ctx.caller == controller.get(), 'Wrong smart contract caller.'
    candidate_state[
        'registered', address] = False  # Registration is lost when no confidence vote. AKA: Stake revoked.


@export
def relinquish():
    assert ctx.caller in election_house.current_value_for_policy(controller.get())

    r = to_be_relinquished.get()
    assert r is None, 'Someone is already trying to relinquish!'

    to_be_relinquished.set(ctx.caller)
