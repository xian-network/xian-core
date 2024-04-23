"""
Base Application
"""


from cometbft.abci.v1beta3.types_pb2 import (
    RequestInitChain,
    ResponseInitChain,
    ResponseCheckTx,
    ResponseFinalizeBlock,
    RequestFinalizeBlock,
    ResponseCommit,
    RequestPrepareProposal,
    RequestProcessProposal,
    RequestExtendVote,
    ResponseExtendVote,
    RequestVerifyVoteExtension,
    ResponseVerifyVoteExtension,
)
from cometbft.abci.v1beta1.types_pb2 import (
    RequestInfo,
    ResponseInfo,
    RequestQuery,
    ResponseQuery,
    RequestLoadSnapshotChunk,
    ResponseLoadSnapshotChunk,
    RequestListSnapshots,
    ResponseListSnapshots,
    RequestOfferSnapshot,
    ResponseOfferSnapshot,
    RequestApplySnapshotChunk,
    ResponseApplySnapshotChunk,
    RequestFlush,
    ResponseFlush,
    RequestEcho,
    ResponseEcho,
)
from cometbft.abci.v1beta2.types_pb2 import (
    ResponsePrepareProposal,
    ResponseProcessProposal,
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
        r = ResponseInitChain()
        r.app_hash = b""
        return r

    def info(self, req: RequestInfo) -> ResponseInfo:
        """
        Called by ABCI when the app first starts. A stateful application
        should alway return the last blockhash and blockheight to prevent Tendermint
        from replaying the transaction log from the beginning.  These values are used
        to help Tendermint determine how to synch the node.
        If blockheight == 0, Tendermint will call ``init_chain()``
        """
        r = ResponseInfo()
        return r

    def check_tx(self, tx: bytes) -> ResponseCheckTx:
        """
        Use to validate incoming transactions.  If the returned resp.code is 0 (OK),
        the tx will be added to Tendermint's mempool for consideration in a block.
        A non-zero response code implies an error and the transaction will be rejected
        """
        return ResponseCheckTx(code=OkCode)
    
    def finalize_block(self, req: RequestFinalizeBlock) -> ResponseFinalizeBlock:
        r = ResponseFinalizeBlock()
        r.app_hash = b""
        r.validator_updates = None
        r.consensus_param_updates = None
        return ResponseFinalizeBlock()

    def query(self, req: RequestQuery) -> ResponseQuery:
        """
        This is commonly used to query the state of the application.
        A non-zero 'code' in the response is used to indicate an error.
        """
        return ResponseQuery(code=OkCode)

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

    def prepare_proposal(
        self, req: RequestPrepareProposal
    ) -> ResponsePrepareProposal:
        """
        Consensus: Prepare proposal
        """
        return ResponsePrepareProposal()
    
    def process_proposal(
        self, req: RequestProcessProposal
    ) -> ResponseProcessProposal:
        """
        Consensus: Process proposal
        """
        return ResponseProcessProposal()
    
    def extend_vote(
        self, req: RequestExtendVote
    ) -> ResponseExtendVote:
        """
        Consensus: Extend vote
        """
        return ResponseExtendVote()
    
    def verify_vote_extension(
        self, req: RequestVerifyVoteExtension
    ) -> ResponseVerifyVoteExtension:
        """
        Consensus: Verify vote extension
        """
        return ResponseVerifyVoteExtension()
    
    def flush(self, req: RequestFlush) -> ResponseFlush:
        """
        Consensus: Flush
        """
        r = ResponseFlush()
        return r
    
    def echo(self, req: RequestEcho) -> ResponseEcho:
        """
        Consensus: Echo
        """
        return ResponseEcho()
