import election_house

S = Hash()

@construct
def seed(initial_rate: int=100,
         master_contract='masternodes',
         election_max_length=datetime.DAYS * 1):

    S['value'] = initial_rate
    S['master_contract'] = master_contract
    S['election_max_length'] = election_max_length

    S['vote_count'] = 1

    reset_current_votes()


def reset_current_votes():
    S['current_total'] = S['value']

@export
def current_value():
    return S['value']

@export
def vote(vk: str, obj: int):
    # Start a new election
    if S['election_start'] is None:
        total_nodes = len(election_house.current_value_for_policy(S['master_contract']))

        S['vote_count'] = 1
        S['min_votes_required'] = (total_nodes * 2 // 3) + 1

        # Set start to now
        S['election_start'] = now
        S.clear('has_voted')

        reset_current_votes()

        tally_vote(vk, obj)

    else:
        tally_vote(vk, obj)

        if election_is_over():
            update_value()

            # Reset everything
            S['election_start'] = None


def update_value():
    S['value'] = int(S['current_total'] / S['vote_count']) or 1


def election_is_over():
    return S['vote_count'] >= S['min_votes_required'] or \
           now - S['election_start'] >= S['election_max_length']


def tally_vote(vk: str, obj: int):
    validate_vote(vk, obj)

    S['current_total'] += obj

    S['has_voted', vk] = True
    S['vote_count'] += 1


def validate_vote(vk: str, obj: int):
    assert vk in election_house.current_value_for_policy(S['master_contract']), 'Not allowed to vote!'

    assert isinstance(obj, int), 'Pass an int!'
    assert obj > 0, 'No negatives!'

    assert S['value'] / 2 <= obj <= S['value'] * 2, 'Out of range!'

    assert S['has_voted', vk] is None, 'Already voted!'
