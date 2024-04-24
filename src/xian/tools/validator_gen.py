from argparse import ArgumentParser
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder, Base64Encoder
from pathlib import Path

import hashlib
import json

"""
Generate priv_validator_key.json file for your validator node
"""


class ValidatorGen:
    def __init__(self):
        parser = ArgumentParser(description='Validator File Generator')
        parser.add_argument(
            '--validator_privkey',
            type=str,
            help="Validator's private key",
            required=True
        )
        parser.add_argument(
            '--output-path',
            type=Path,
            default=None,
            help="Path to save generated file"
        )
        self.args = parser.parse_args()

    def generate_keys(self):
        pk_hex = self.args.validator_privkey

        # Convert hex private key to bytes and generate signing key object
        signing_key = SigningKey(pk_hex, encoder=HexEncoder)

        # Obtain the verify key (public key) from the signing key
        verify_key = signing_key.verify_key

        # Concatenate private and public key bytes
        priv_key_with_pub = signing_key.encode() + verify_key.encode()

        # Encode concatenated private and public keys in Base64 for the output
        priv_key_with_pub_b64 = Base64Encoder.encode(priv_key_with_pub).decode('utf-8')

        # Encode public key in Base64 for the output
        public_key_b64 = verify_key.encode(encoder=Base64Encoder).decode('utf-8')

        # Hash the public key using SHA-256 and take the first 20 bytes for the address
        address_bytes = hashlib.sha256(verify_key.encode()).digest()[:20]
        address = address_bytes.hex().upper()

        output = {
            "address": address,
            "pub_key": {
                "type": "tendermint/PubKeyEd25519",
                "value": public_key_b64
            },
            'priv_key': {
                'type': 'tendermint/PrivKeyEd25519',
                'value': priv_key_with_pub_b64
            }
        }
        return output

    def main(self):
        output_path = Path(self.args.output_path) if self.args.output_path else Path.cwd()
        output_file = output_path / Path('priv_validator_key.json')

        if len(self.args.validator_privkey) != 64:
            print('Validator private key must be 64 characters')
            return
        
        keys = self.generate_keys()

        with open(output_file, 'w') as f:
            f.write(json.dumps(keys, indent=2))


if __name__ == '__main__':
    ValidatorGen().main()
