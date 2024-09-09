import hashlib
from contracting.storage.encoder import encode, decode

def hash_list(obj: list) -> bytes:
    encoded_tx = encode("".join(obj)).encode()
    hash_sha3 = hashlib.sha3_256()
    hash_sha3.update(encoded_tx)
    return hash_sha3.hexdigest().encode("utf-8")


def hash_from_rewards(rewards):
    h = hashlib.sha3_256()
    encoded_rewards = encode(rewards).encode()
    h.update(encoded_rewards)
    return h.hexdigest()


def hash_from_validator_updates(validator_updates):
    h = hashlib.sha3_256()
    
    if not validator_updates:  # Check if the list is empty
        # Use a consistent value to hash when the list is empty
        h.update(b'')  # Hash of an empty byte sequence
    else:
        # Serialize each validator update using protobuf's SerializeToString() method
        for update in validator_updates:
            encoded_update = update.SerializeToString()
            h.update(encoded_update)
    
    return h.hexdigest()