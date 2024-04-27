# Actions
INTRODUCE_MOTION = 'introduce_motion'
VOTE_ON_MOTION = 'vote_on_motion'

# Motions
NO_MOTION = 0
REMOVE_MEMBER = 1
ADD_SEAT = 2
REMOVE_SEAT = 3
CHANGE_MINIMUM = 4
CHANGE_UNBONDING_PERIOD = 5

VOTING_PERIOD = datetime.DAYS * 1

S = Hash()
minimum_nodes = Variable()
candidate_contract = Variable()
unbonding_period = Variable()


@construct
def seed(initial_members: list, minimum: int=1, candidate: str='elect_members'):
    S['members'] = initial_members
    S['scheduled_for_removal'] = {}
    minimum_nodes.set(minimum)
    candidate_contract.set(candidate)
    unbonding_period.set(datetime.DAYS * 7)

    S['yays'] = 0
    S['nays'] = 0

    S['current_motion'] = NO_MOTION
    S['motion_opened'] = now

@export
def quorum_max():
    return int(len(S['members']) * 2 / 3) + 1

@export
def quorum_min():
    return min(quorum_max(), minimum_nodes.get())

@export
def current_value():
    return {"members": S['members'], "scheduled_for_removal": S['scheduled_for_removal']}

@export
def remove_from_scheduled_removal(vk: str):
    assert ctx.caller == candidate_contract.get(), 'Not authorized.'
    scheduled_for_removal = S['scheduled_for_removal']
    assert vk in scheduled_for_removal, 'VK not scheduled for removal.'
    scheduled_for_removal.pop(vk)
    S['scheduled_for_removal'] = scheduled_for_removal
    remove_from_members(vk)

def remove_from_members(vk: str):
    members = S['members']
    assert vk in members, 'VK not in members.'
    members.remove(vk)
    S['members'] = members

@export
def i_quit():
    assert ctx.caller in S['members'], 'Not a member.'
    assert len(S['members']) > minimum_nodes.get(), 'Cannot drop below current quorum.'
    scheduled_for_removal = S['scheduled_for_removal']
    scheduled_for_removal[ctx.caller] = now + unbonding_period.get()
    S['scheduled_for_removal'] = scheduled_for_removal

@export
def vote(vk: str, obj: list):
    assert isinstance(obj, list), 'Pass a list!'

    arg = None

    if len(obj) == 3:
        action, position, arg = obj
    else:
        action, position = obj

    assert_vote_is_valid(vk, action, position, arg)

    if action == INTRODUCE_MOTION:
        introduce_motion(position, arg)

    else:
        assert S['current_motion'] != NO_MOTION, 'No motion proposed.'

        if now - S['motion_opened'] >= VOTING_PERIOD:
            reset()

        assert S['positions', vk] is None, 'VK already voted.'

        if position is True:
            S['yays'] += 1
            S['positions', vk] = position
        else:
            S['nays'] += 1
            S['positions', vk] = position

        if S['yays'] >= len(S['members']) // 2 + 1:
            pass_current_motion()
            reset()

        elif S['nays'] >= len(S['members']) // 2 + 1:
            reset()


def assert_vote_is_valid(vk: str, action: str, position: bool, arg: Any=None):
    assert vk in S['members'], 'Not a member.'

    assert action in [INTRODUCE_MOTION, VOTE_ON_MOTION], 'Invalid action.'

    if action == INTRODUCE_MOTION:
        assert S['current_motion'] == NO_MOTION, 'Already in motion.'
        assert 0 < position <= REMOVE_SEAT, 'Invalid motion.'
        if position == REMOVE_MEMBER:
            assert_vk_is_valid(arg)

    elif action == VOTE_ON_MOTION:
        assert isinstance(position, bool), 'Invalid position'


def assert_vk_is_valid(vk: str):
    assert vk is not None, 'No VK provided.'
    assert isinstance(vk, str), 'VK not a string.'
    assert len(vk) == 64, 'VK is not 64 characters.'
    # assert vk == ctx.signer, 'Signer has to be the one voting to remove themselves.'
    int(vk, 16)


def introduce_motion(position: int, arg: Any):
    # If remove member, must be a member that already exists
    assert position <= REMOVE_SEAT, 'Invalid position.'
    if position == REMOVE_MEMBER:
        assert arg in S['members'], 'Member does not exist.'
        assert len(S['members']) > minimum_nodes.get(), 'Cannot drop below current quorum.'
        S['member_in_question'] = arg
    if position == CHANGE_MINIMUM:
        assert arg > 0, 'Minimum must be greater than zero.'
        assert isinstance(arg, int), 'Minimum must be an integer.'
        S['proposed_minimum'] = arg
    if position == CHANGE_UNBONDING_PERIOD:
        assert arg > 0, 'Unbonding period must be greater than zero.'
        assert isinstance(arg, int), 'Unbonding period must be an integer.'
        S['proposed_unbonding_period'] = arg

    S['current_motion'] = position
    S['motion_opened'] = now


def pass_current_motion():
    current_motion = S['current_motion']
    members = S['members']

    if current_motion == REMOVE_MEMBER:
        members.remove(S['member_in_question'])

    elif current_motion == ADD_SEAT:
        # Get the top member
        member_candidates = importlib.import_module(candidate_contract.get())
        new_mem = member_candidates.top_member()

        # Append it to the list, and remove it from pending
        if new_mem is not None:
            members.append(new_mem)
            member_candidates.pop_top()

    elif current_motion == REMOVE_SEAT:
        # Get least popular member
        member_candidates = importlib.import_module(candidate_contract.get())
        old_mem = member_candidates.last_member()

        # Remove them from the list and pop them from deprecating
        if old_mem is not None:
            scheduled_for_removal = S['scheduled_for_removal']
            scheduled_for_removal[old_mem] = now + unbonding_period.get()
            S['scheduled_for_removal'] = scheduled_for_removal
            member_candidates.pop_last()

    elif current_motion == CHANGE_MINIMUM:
        minimum_nodes.set(S['proposed_minimum'])
        S['proposed_minimum'] = None

    elif current_motion == CHANGE_UNBONDING_PERIOD:
        unbonding_period.set(datetime.DAYS * S['proposed_unbonding_period'])
        S['proposed_unbonding_period'] = None

    S['members'] = members


def reset():
    S['current_motion'] = NO_MOTION
    S['member_in_question'] = None
    S['yays'] = 0
    S['nays'] = 0
    S.clear('positions')
