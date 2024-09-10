from cometbft.abci.v1beta1.types_pb2 import ValidatorUpdate
from cometbft.crypto.v1.keys_pb2 import PublicKey
import requests
import base64
import logging


class ValidatorHandler:
    def __init__(self, app):
        self.client = app.client
       
    def get_validators_from_state(self) -> list[str]:
        validators = self.client.raw_driver.get("masternodes.nodes")
        return validators
    
    def get_tendermint_validators(self) -> list[str]:
        try:
            response = requests.get("http://localhost:26657/validators")
            validators = [base64.b64decode(validator['pub_key']['value']).hex() for validator in response.json()['result']['validators'] if int(validator['voting_power']) > 0]
        except Exception as e:
            validators = []
        return validators
    
    def to_bytes(self, data: str) -> bytes:
        return bytes.fromhex(data)
    
    def build_validator_updates(self, height) -> list[ValidatorUpdate]:
        validators_state = self.get_validators_from_state()
        validators_tendermint = self.get_tendermint_validators()
        if len(validators_tendermint) == 0:
            logging.error("Failed to get validators from tendermint")
            return []
        updates = []
        for validator in validators_state:
            if validator not in validators_tendermint:
                updates.append(ValidatorUpdate(pub_key=PublicKey(ed25519=self.to_bytes(validator)), power=10))
                logging.info(f"Adding {validator} to tendermint validators")
        for validator in validators_tendermint:
            if validator not in validators_state:
                updates.append(ValidatorUpdate(pub_key=PublicKey(ed25519=self.to_bytes(validator)), power=0))
                logging.info(f"Removing {validator} from tendermint validators")

        return updates
