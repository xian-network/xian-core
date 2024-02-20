import pathlib
from contracting import config
from contracting.db.driver import ContractDriver, FSDriver

NONCE_FILENAME = '__n'
PENDING_NONCE_FILENAME = '__pn'
STORAGE_HOME = pathlib.Path().home().joinpath('.tendermint/xian')

class NonceStorage:
    def __init__(self, root=None):
        root = root if root is not None else STORAGE_HOME
        self.driver = FSDriver(root=root)

    # Move this to transaction.py
    def get_nonce(self, sender):
        return self.driver.get(NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER)

    # Move this to transaction.py
    def get_pending_nonce(self, sender):
        return self.driver.get(PENDING_NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER)

    def set_nonce(self, sender, value):
        self.driver.set(
            NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER,
            value
        )

    def safe_set_nonce(self, sender, value):
        current_nonce = self.get_nonce(sender=sender)

        if current_nonce is None:
            current_nonce = -1

        if value > current_nonce:
            self.driver.set(
                NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER,
                value
            )

    def set_pending_nonce(self, sender, value):
        self.driver.set(
            PENDING_NONCE_FILENAME + config.INDEX_SEPARATOR + sender + config.DELIMITER,
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
        self.driver.flush_file(NONCE_FILENAME)
        self.driver.flush_file(PENDING_NONCE_FILENAME)

    def flush_pending(self):
        self.driver.flush_file(PENDING_NONCE_FILENAME)