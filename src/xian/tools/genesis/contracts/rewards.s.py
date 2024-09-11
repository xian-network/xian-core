S = Hash()

@construct
def seed(initial_split: list = [0.88, 0.01, 0.01, 0.1]):
    S['value'] = initial_split

@export
def current_value():
    return S['value']

@export
def set_value(new_value: list):
    assert len(new_value) == 4, 'New value must be a list of 4 elements'
    assert sum(new_value) == 1, 'Sum of new value must be 1'
    assert all([x > 0 for x in new_value]), 'All elements of new value must be greater'
    S['value'] = new_value