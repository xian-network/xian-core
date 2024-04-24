# Convenience
I = importlib

# Policies
policies = Hash()

# Policy interface
policy_interface = [
    I.Func('vote', args=('vk', 'obj')),
    I.Func('current_value')
]


@export
def register_policy(contract: str):
    if policies[contract] is None:
        # Attempt to import the contract to make sure it is already submitted
        p = I.import_module(contract)

        # Assert ownership is election_house and interface is correct
        assert I.owner_of(p) == ctx.this, \
            'Election house must control the policy contract!'

        assert I.enforce_interface(p, policy_interface), \
            'Policy contract does not follow the correct interface'

        policies[contract] = True
    else:
        raise Exception('Policy already registered')


@export
def current_value_for_policy(policy: str):
    assert policies[policy] is not None, f'Invalid policy: {policy}.'
    p = I.import_module(policy)

    return p.current_value()


@export
def vote(policy: str, value: Any):
    # Verify policy has been registered
    assert policies[policy] is not None, 'Invalid policy.'
    p = I.import_module(policy)

    p.vote(vk=ctx.caller, obj=value)
