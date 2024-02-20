class TransactionException(Exception):
    pass


class TransactionSignatureInvalid(TransactionException):
    pass


class TransactionPOWProofInvalid(TransactionException):
    pass


class TransactionProcessorInvalid(TransactionException):
    pass


class TransactionTooManyPendingException(TransactionException):
    pass


class TransactionNonceInvalid(TransactionException):
    pass


class TransactionStampsNegative(TransactionException):
    pass


class TransactionSenderTooFewStamps(TransactionException):
    pass


class TransactionContractNameInvalid(TransactionException):
    pass


class TransactionFormattingError(TransactionException):
    pass


class TransactionTrailingZerosFixedError(TransactionException):
    pass


class TransactionStaleError(TransactionException):
    pass


class TransactionInvalidTimestampError(TransactionException):
    pass

EXCEPTION_MAP = {
    TransactionNonceInvalid: {"error": "Transaction nonce is invalid."},
    TransactionProcessorInvalid: {
        "error": "Transaction processor does not match expected processor."
    },
    TransactionTooManyPendingException: {
        "error": "Too many pending transactions currently in the block."
    },
    TransactionSenderTooFewStamps: {
        "error": "Transaction sender has too few stamps for this transaction."
    },
    TransactionPOWProofInvalid: {"error": "Transaction proof of work is invalid."},
    TransactionSignatureInvalid: {"error": "Transaction is not signed by the sender."},
    TransactionStampsNegative: {"error": "Transaction has negative stamps supplied."},
    TransactionException: {"error": "Another error has occurred."},
    TransactionFormattingError: {"error": "Transaction is not formatted properly."},
    TransactionTrailingZerosFixedError: {
        "error": "Transaction contains illegal trailing zeros in a Fixed object."
    },
    TransactionStaleError: {"error": "Transaction timestamp is too old. Submit again."},
    TransactionInvalidTimestampError: {"error": "Transaction timestamp is invalid."},
    TransactionContractNameInvalid: {"error": "Transaction contract name is invalid."},
}