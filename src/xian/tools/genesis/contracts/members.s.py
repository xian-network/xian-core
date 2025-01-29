import dao
import rewards
import stamp_cost
import currency

nodes = Variable()
votes = Hash(default_value=False) # votes[id] = {"yes": int, "no": int, type: str, arg: Any, "voters": list, "finalized": bool}
total_votes = Variable()
types = Variable()

registration_fee = Variable()
pending_registrations = Hash(default_value=False)
pending_leave = Hash(default_value=False)
holdings = Hash(default_value=0)

PASS_THRESHOLD = 0.8
PROPOSAL_EXPIRY_DAYS = 7

@construct
def seed(genesis_nodes: list, genesis_registration_fee: int):
    nodes.set(genesis_nodes)
    types.set([
        "add_member", 
        "remove_member", 
        "change_registration_fee", 
        "reward_change", 
        "dao_payout", 
        "stamp_cost_change", 
        "change_types", 
        "create_stream", 
        "change_close_time", 
        "finalize_stream", 
        "close_balance_finalize",
        "topic_vote"
    ])
    total_votes.set(0)
    registration_fee.set(genesis_registration_fee)

@export
def propose_vote(type_of_vote: str, arg: Any):
    assert ctx.caller in nodes.get(), "Only nodes can propose new votes"

    if type_of_vote == "add_member":
        assert pending_registrations[arg] == True, "Member must have pending registration"
    
    assert type_of_vote in types.get(), "Invalid type"
    proposal_id = total_votes.get() + 1
    votes[proposal_id] = {
        "yes": 1,
        "no": 0,
        "type": type_of_vote,
        "arg": arg,
        "voters": [ctx.caller],
        "finalized": False,
        "expiry": now + datetime.timedelta(days=PROPOSAL_EXPIRY_DAYS)
    }
    total_votes.set(proposal_id)
    
    decide_finalize(proposal_id)

    return votes[proposal_id]

@export
def vote(proposal_id: int, vote: str):
    assert ctx.caller in nodes.get(), "Only nodes can vote"
    assert votes[proposal_id], "Invalid proposal"
    assert votes[proposal_id]["finalized"] == False, "Proposal already finalized"
    assert now < votes[proposal_id]["expiry"], "Proposal expired"
    assert vote in ["yes", "no"], "Invalid vote"
    assert ctx.caller not in votes[proposal_id]["voters"], "Already voted"

    # Do this because we can't modify a dict in a hash without reassigning it
    cur_vote = votes[proposal_id]
    cur_vote[vote] += 1
    cur_vote["voters"].append(ctx.caller)
    votes[proposal_id] = cur_vote

    # Check if > PASS_THRESHOLD * of nodes have voted "yes"
    decide_finalize(proposal_id)

    return cur_vote

def decide_finalize(proposal_id: int):
    cur_vote = votes[proposal_id]
    ayes_needed = (len(nodes.get()) * PASS_THRESHOLD)
    ayes = cur_vote["yes"]

    if ayes >= ayes_needed:
        finalize_vote(proposal_id)

def get_yes_vote_pct(proposal_id: int):
    cur_vote = votes[proposal_id]
    return cur_vote["yes"] / (cur_vote["yes"] + cur_vote["no"])

def finalize_vote(proposal_id: int):
    cur_vote = votes[proposal_id]

    if cur_vote["type"] == "add_member":
        assert pending_registrations[cur_vote["arg"]], "Member must have pending registration"
        nodes.set(nodes.get() + [cur_vote["arg"]])
    elif cur_vote["type"] == "remove_member":
        nodes.set([node for node in nodes.get() if node != cur_vote["arg"]])
        force_leave(cur_vote["arg"])
    elif cur_vote["type"] == "reward_change":
        rewards.set_value(new_value=cur_vote["arg"])
    elif cur_vote["type"] == "dao_payout":
        dao.transfer_from_dao(args=cur_vote["arg"])
    elif cur_vote["type"] == "stamp_cost_change":
        stamp_cost.set_value(new_value=cur_vote["arg"])
    elif cur_vote["type"] == "change_registration_fee":
        registration_fee.set(cur_vote["arg"])
    elif cur_vote["type"] == "change_types":
        types.set(cur_vote["arg"])
    elif cur_vote["type"] == "create_stream":
        dao.create_stream(args=cur_vote["arg"])
    elif cur_vote["type"] == "change_close_time":
        dao.change_close_time(args=cur_vote["arg"])
    elif cur_vote["type"] == "finalize_stream":
        dao.finalize_stream(args=cur_vote["arg"])
    elif cur_vote["type"] == "close_balance_finalize":
        dao.close_balance_finalize(args=cur_vote["arg"])
    
    cur_vote["finalized"] = True
    votes[proposal_id] = cur_vote
    return cur_vote

@export
def balance_stream(stream_id: str):
    return dao.balance_stream(stream_id=stream_id)

def force_leave(node: str):
    pending_leave[node] = now + datetime.timedelta(days=7)

@export
def announce_leave():
    assert ctx.caller in nodes.get(), "Not a node"
    assert pending_leave[ctx.caller] == False, "Already pending leave"
    pending_leave[ctx.caller] = now + datetime.timedelta(days=7)
    
@export
def leave():
    assert pending_leave[ctx.caller], "Not pending leave"
    assert pending_leave[ctx.caller] < now, "Leave announcement period not over"
    if ctx.caller in nodes.get():
        nodes.set([node for node in nodes.get() if node != ctx.caller])
    pending_leave[ctx.caller] = False

@export
def register():
    assert ctx.caller not in nodes.get(), "Already a node"
    assert pending_registrations[ctx.caller] == False, "Already pending registration"
    currency.transfer_from(amount=registration_fee.get(), to=ctx.this, main_account=ctx.caller)
    holdings[ctx.caller] = registration_fee.get()
    pending_registrations[ctx.caller] = True

@export
def unregister():
    assert ctx.caller not in nodes.get(), "If you're a node already, you can't unregister. You need to leave or be removed."
    assert pending_registrations[ctx.caller] == True, "No pending registration"
    if holdings[ctx.caller] > 0:
        currency.transfer(holdings[ctx.caller], ctx.caller)
    pending_registrations[ctx.caller] = False
    holdings[ctx.caller] = 0
