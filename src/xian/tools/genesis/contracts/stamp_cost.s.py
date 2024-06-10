S = Hash()

@construct
def seed(initial_rate: int=100):
    S['value'] = initial_rate

@export
def current_value():
    return S['value']

@export
def set_value(new_value: int):
    assert new_value > 0, 'New value must be greater than 0'
    S['value'] = new_value
