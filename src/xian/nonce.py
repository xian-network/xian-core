from xian.constants import Constants as c
from xian.exceptions import TransactionException

from contracting import constants as config


class NonceStorage:
    def __init__(self, client, root=None):
        root = root if root is not None else c.STORAGE_HOME
        self.client = client

    def check_nonce(self, tx: dict):
        tx_nonce = tx["payload"]["nonce"]
        tx_sender = tx["payload"]["sender"]
        current_nonce = self.get_nonce(sender=tx_sender)

        if not (current_nonce is None or tx_nonce > current_nonce):
            raise TransactionException('Transaction nonce is invalid')
        
    def set_nonce_by_tx(self, tx):
        self.client.raw_driver.set(
            c.NONCE_FILENAME + config.INDEX_SEPARATOR + tx['payload']['sender'] + config.DELIMITER,
            tx['payload']['nonce']
        )

    def set_nonce(self, sender, value):
        self.client.raw_driver.set(
            c.NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER,
            value
        )

    # Move this to transaction.py
    def get_nonce(self, sender):
        return self.client.raw_driver.get(c.NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER)

    # Move this to transaction.py
    def get_pending_nonce(self, sender):
        return self.client.raw_driver.get(c.PENDING_NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER)

    def safe_set_nonce(self, sender, value):
        current_nonce = self.get_nonce(sender=sender)

        if current_nonce is None:
            current_nonce = -1

        if value > current_nonce:
            self.client.raw_driver.set(
                c.NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER,
                value
            )

    def set_pending_nonce(self, sender, value):
        self.client.raw_driver.set(
            c.PENDING_NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER,
            value
        )

    # Move this to webserver.py
    def get_latest_nonce(self, sender):
        latest_nonce = self.get_pending_nonce(sender=sender)

        if latest_nonce is None:
            latest_nonce = self.get_nonce(sender=sender)

        if latest_nonce is None:
            latest_nonce = 0

        return latest_nonce

    def get_next_nonce(self, sender):
        current_nonce = self.get_pending_nonce(sender=sender)

        if current_nonce is None:
            current_nonce = self.get_nonce(sender=sender)

        if current_nonce is None:
            return 0

        return current_nonce + 1

    def flush(self):
        self.client.raw_driver.flush_file(c.NONCE_FILENAME)
        self.client.raw_driver.flush_file(c.PENDING_NONCE_FILENAME)

    def flush_pending(self):
        self.client.raw_driver.flush_file(c.PENDING_NONCE_FILENAME)
