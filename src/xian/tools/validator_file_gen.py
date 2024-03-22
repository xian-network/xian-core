from argparse import ArgumentParser
from nacl.public import PrivateKey
from base64 import b64encode
import json
import hashlib

"""
This is to generate the priv_validator_key.json file for your validator node.
"""

class ValidatorGen:
    def __init__(self):
        self.parser = ArgumentParser(description='Validator File Generator')
        self.parser.add_argument('--validator_privkey', type=str, help='Validator wallet private key 64 characters', required=True)
        self.args = self.parser.parse_args()

    def generate_keys(self):
        validator_sk_hex = bytes.fromhex(self.args.validator_privkey)
        validator_sk = PrivateKey(validator_sk_hex)

        validator_pub_key = validator_sk.public_key

        validator_pub_key_b64 = b64encode(validator_pub_key._public_key).decode('utf-8')
        validator_sk_b64 = b64encode(validator_sk._private_key + validator_pub_key._public_key).decode('utf-8')

        validator_pub_key_hash = hashlib.sha256(validator_pub_key._public_key).digest()[:20]
        validator_address = validator_pub_key_hash.hex().upper()


        return {
            'address': validator_address,
            'pub_key': {
                'type': 'tendermint/PubKeyEd25519',
                'value': validator_pub_key_b64
            },
            'priv_key': {
                'type': 'tendermint/PrivKeyEd25519',
                'value': validator_sk_b64
            }
        }
    
    def main(self):
        
        if len(self.args.validator_privkey) != 64:
            print('Validator private key must be 64 characters')
            return
        
        keys = self.generate_keys()

        with open('priv_validator_key.json', 'w') as f:
            f.write(json.dumps(keys, indent=2))

if __name__ == '__main__':
    validator_gen = ValidatorGen()
    validator_gen.main()