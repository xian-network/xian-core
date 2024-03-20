from cometbft.abci.v1beta1.types_pb2 import ValidatorUpdate
from cometbft.crypto.v1.keys_pb2 import PublicKey
import requests
import base64

class ValidatorHandler():
    def __init__(self, app):
        self.driver = app.driver
        self.app = app
       
    def get_validators_from_state(self) -> list[str]:
        validators = self.driver.get("masternodes.S:members")
        return validators
    
    def get_tendermint_validators(self) -> list[str]:
        response = requests.get("http://localhost:26657/validators")
        validators = [base64.b64decode(validator['pub_key']['value']).hex() for validator in response.json()['result']['validators'] if int(validator['voting_power']) > 0]
        return validators
    
    def to_bytes(self, data: str) -> bytes:
        return bytes.fromhex(data)
    
    def build_validator_updates(self) -> list[ValidatorUpdate]:
        validators_state = self.get_validators_from_state()
        validators_tendermint = self.get_tendermint_validators()
        updates = []
        for validator in validators_state:
            if validator not in validators_tendermint:
                updates.append(ValidatorUpdate(pub_key=PublicKey(ed25519=self.to_bytes(validator)), power=10))
                print(f"Adding {validator} to tendermint validators")
        for validator in validators_tendermint:
            if validator not in validators_state:
                updates.append(ValidatorUpdate(pub_key=PublicKey(ed25519=self.to_bytes(validator)), power=0))
                print(f"Removing {validator} from tendermint validators")
        if len(updates) > 0:
            print(f"Pushing validator updates")
        return updates