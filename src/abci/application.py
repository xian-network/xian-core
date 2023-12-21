"""
Base Application

The Tendermint server will create 4 connections to the ABCI Server:
- Query:
    ``info()``
    ``query()``
- Mempool:
    ``check_tx()``
- Consensus:
    ``init_chain()``
    ``begin_block()``
    ``deliver_tx()``
    ``end_block()``
    ``commit()``
State Sync:
    ``list_snapshots()``
    ``offer_snapshots()``
    ``load_snapshot_chunks()``
    ``apply_snapshot_chunks()``

Each of these calls are handled below
"""


from tendermint.abci.types_pb2 import (
    RequestInfo,
    ResponseInfo,
    RequestInitChain,
    ResponseInitChain,
    ResponseCheckTx,
    ResponseDeliverTx,
    RequestQuery,
    ResponseQuery,
    RequestBeginBlock,
    ResponseBeginBlock,
    RequestEndBlock,
    ResponseEndBlock,
    ResponseCommit,
    RequestLoadSnapshotChunk,
    ResponseLoadSnapshotChunk,
    RequestListSnapshots,
    ResponseListSnapshots,
    RequestOfferSnapshot,
    ResponseOfferSnapshot,
    RequestApplySnapshotChunk,
    ResponseApplySnapshotChunk,
)


# Common response code

# All is good
OkCode = 0
# There was a problem...
ErrorCode = 1



class BaseApplication:
    """
    Base ABCI Application. Extend this and override what's needed for your app
    """
        

    def init_chain(self, req: RequestInitChain) -> ResponseInitChain:
        """
        Called once, after ``info()`` during startup, when block height is 0  
        This is where you can load initial ``genesis`` data, etc....
        See ``info()``
        - Load genesis
        - Bootstrap Contracts
        - Initial delegate set.
        """
        return ResponseInitChain()

    def info(self, req: RequestInfo) -> ResponseInfo:
        """
        Called by ABCI when the app first starts. A stateful application
        should alway return the last blockhash and blockheight to prevent Tendermint
        from replaying the transaction log from the beginning.  These values are used
        to help Tendermint determine how to synch the node.
        If blockheight == 0, Tendermint will call ``init_chain()``
        """
        r = ResponseInfo()
        r.last_block_height = 0
        r.last_block_app_hash = b""
        return r

    def deliver_tx(self, tx: bytes) -> ResponseDeliverTx:
        """
        This is called via the consensus connection.

        Process the transaction, apply state changes (storing stuff),
        and return the approriate ``code`` in  ``ResponseDeliverTx``.
        A code of zero means the computation was successful.
        A non-zero response code implies an error. However, the transaction
        will still be included in the block, but marked as invalid via the ``code``
        """

        return ResponseDeliverTx(code=OkCode)

    def check_tx(self, tx: bytes) -> ResponseCheckTx:
        """
        Use to validate incoming transactions.  If the returned resp.code is 0 (OK),
        the tx will be added to Tendermint's mempool for consideration in a block.
        A non-zero response code implies an error and the transaction will be rejected
        """
        return ResponseCheckTx(code=OkCode)

    def query(self, req: RequestQuery) -> ResponseQuery:
        """
        This is commonly used to query the state of the application.
        A non-zero 'code' in the response is used to indicate an error.
        """
        return ResponseQuery(code=OkCode)

    def begin_block(self, req: RequestBeginBlock) -> ResponseBeginBlock:
        """
        Called during the consensus process.

        You can use this to do ``something`` for each new block.
        The overall flow of the calls are:
        begin_block()
         for each tx:
           deliver_tx(tx)
        end_block()
        commit()
        """
        return ResponseBeginBlock()

    def end_block(self, req: RequestEndBlock) -> ResponseEndBlock:
        """
        Called at the end of processing the current block. If this is a stateful application
        you can use the height from the request to record the last_block_height
        """
        return ResponseEndBlock()

    def commit(self) -> ResponseCommit:
        """
        Called after ``end_block``.  This should return a compact ``fingerprint``
        of the current state of the application. This is usually the root hash
        of a merkletree.  The returned data is used as part of the consensus process.
        """
        return ResponseCommit()

    def list_snapshots(
        self, req: RequestListSnapshots
    ) -> ResponseListSnapshots:
        """
        State sync: return state snapshots
        """
        return ResponseListSnapshots()

    def offer_snapshot(
        self, req: RequestOfferSnapshot
    ) -> ResponseOfferSnapshot:
        """
        State sync: Offer a snapshot to the application
        """
        return ResponseOfferSnapshot()

    def load_snapshot_chunk(
        self, req: RequestLoadSnapshotChunk
    ) -> ResponseLoadSnapshotChunk:
        """
        State sync: Load a snapshot
        """
        return ResponseLoadSnapshotChunk()

    def apply_snapshot_chunk(
        self, req: RequestApplySnapshotChunk
    ) -> ResponseApplySnapshotChunk:
        """
        State sync: Apply a snapshot to state
        """
        return ResponseApplySnapshotChunk()
