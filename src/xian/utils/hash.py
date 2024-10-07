import hashlib
from contracting.storage.encoder import encode

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
