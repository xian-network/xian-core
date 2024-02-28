from tendermint.abci.types_pb2 import ValidatorUpdate
from tendermint.crypto.keys_pb2 import PublicKey
import requests
import base64

class ValidatorHandler():
    def __init__(self, app):
        self.driver = app.driver
        self.app = app
       
    def get_validators_from_state(self) -> list[str]:
        validators = self.driver.get("masternodes.S:members")
        print(f"Current state validators: {validators}")
        return validators
    
    def get_tendermint_validators(self) -> list[str]:
        response = requests.get("http://localhost:26657/validators")
        # Only add the validators that are voting power > 0
        validators = [base64.b64decode(validator['pub_key']['value']).hex() for validator in response.json()['result']['validators'] if int(validator['voting_power']) > 0]
        print(f"Current tendermint validators: {validators}")
        return validators
    
    def build_validator_updates(self) -> list[ValidatorUpdate]:
        validators_state = self.get_validators_from_state()
        validators_tendermint = self.get_tendermint_validators()
        updates = []
        for validator in validators_state:
            if validator not in validators_tendermint:
                updates.append(ValidatorUpdate(pub_key=PublicKey(ed25519=validator), power=10))
                print(f"Adding {validator} to tendermint validators")
        for validator in validators_tendermint:
            if validator not in validators_state:
                updates.append(ValidatorUpdate(pub_key=PublicKey(ed25519=validator), power=0))
                print(f"Removing {validator} from tendermint validators")
        return updates