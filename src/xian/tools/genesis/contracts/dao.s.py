import currency
import election_house

S = Hash()
pending_motions = Variable()

@construct
def seed():
    S['motion_period'] = datetime.DAYS * 1
    S['motion_delay'] = datetime.DAYS * 1
    pending_motions.set({'pending_motions': []})
    reset()

@export
def current_value():
    return pending_motions.get()['pending_motions']

@export
def vote(vk: str, obj: list):
    finalize_pending_motions()

    assert isinstance(obj, list), 'Pass a list!'
    if len(obj) == 0:
        return

    assert vk in election_house.current_value_for_policy('masternodes'), 'Not a member.'

    if S['motion_start'] is None:
        recipient_vk, amount = obj
        assert_recipient_vk_and_amount_is_valid(recipient_vk, amount)

        S['recipient_vk'] = recipient_vk
        S['amount'] = amount
        S['motion_start'] = now
    else:
        if now - S['motion_start'] >= S['motion_period']:
            reset()
            return

        position, = obj
        assert_vote_is_valid(vk, position)

        S['positions', vk] = position
        if position:
            S['yays'] += 1
        else:
            S['nays'] += 1

        total_votes = S['yays'] + S['nays']
        if total_votes >= len(election_house.current_value_for_policy('masternodes')) * 3 // 5 + 1:
            if S['yays'] >= total_votes * 7 // 10 + 1:
                pass_motion()
            elif S['nays'] >= total_votes * 7 // 10 + 1:
                reset()

def pass_motion():
    motions = pending_motions.get()['pending_motions']
    motions += [{
        'motion_passed': now,
        'recipient_vk': S['recipient_vk'],
        'amount': S['amount']
    }]
    pending_motions.set({'pending_motions': motions})
    reset()

def finalize_pending_motions():
    motions = pending_motions.get()['pending_motions']
    for motion in motions[:]:
        if now - motion['motion_passed'] >= S['motion_delay']:
            currency.transfer(amount=motion['amount'], to=motion['recipient_vk'])
            motions.remove(motion)
    pending_motions.set({'pending_motions': motions})

def reset():
    S['yays'] = 0
    S['nays'] = 0
    S['motion_start'] = None
    S['recipient_vk'] = None
    S['amount'] = None
    S.clear('positions')

def assert_recipient_vk_and_amount_is_valid(vk: str, amount: int):
    assert vk is not None, 'No recipient VK provided.'
    assert isinstance(vk, str), 'Recipient VK is not a string.'
    assert len(vk) == 64, 'Recipient VK is not 64 characters.'
    int(vk, 16)

    assert amount is not None, 'No amount provided.'
    assert isinstance(amount, int), 'Amount is not an integer.'
    assert amount > 0, 'Amount is not greater than zero.'

def assert_vote_is_valid(vk: str, position: bool):
    assert S['positions', vk] is None, 'VK already voted.'
    assert isinstance(position, bool), 'Invalid position.'
