# State Patches

This directory contains state patches that will be applied at specific block heights during blockchain execution.

## Purpose

State patches allow administrators to correct blockchain state without requiring forks or resets of the network. This is useful for:

- Fixing bugs that resulted in incorrect state
- Correcting values after protocol upgrades
- Implementing governance decisions that modify state
- Providing emergency remediation for security issues
- Deploying or updating smart contracts without transactions

## File Format

State patches are stored in `state_patches.json` using the following format:

```json
{
  "BLOCK_HEIGHT": [
    {
      "key": "contract.path:identifier",
      "value": <value>,
      "comment": "Explanation of why this change is necessary"
    },
    ...more patches for this height...
  ],
  "ANOTHER_BLOCK_HEIGHT": [
    ...patches for another block height...
  ]
}
```

Where:
- `BLOCK_HEIGHT`: The block height at which the patch will be applied (as a string)
- `key`: The full state key path (contract.path:identifier)
- `value`: The new value to set (can be a string, number, boolean or object)
- `comment`: A description explaining the reason for the patch

## How It Works

1. All patches are loaded into memory when the ABCI application starts
2. During the `finalize_block` phase, the system checks if any patches exist for the current block height
3. If patches exist, they are applied to the state and a hash of the patches is generated
4. The patch hash is included in the block's fingerprint hashes, ensuring that all nodes apply the same patches
5. The state changes are recorded in the blockchain's consensus state

## Database Integration

State patches are fully integrated with the Blockchain Data Service (BDS):

1. **Dedicated State Patches Table**: All state patches are recorded in a dedicated `state_patches` table that tracks:
   - Patch hash
   - Block height, hash, and time
   - Complete patch content including comments

2. **Transaction Records**: Each state patch generates a transaction record with a unique hash of format `STATE_PATCH_{block_height}` that:
   - Links state changes to a specific patch
   - Provides audit trail in transaction history
   - Maintains database referential integrity

3. **Special Contract Handling**: When a patch includes contract code (keys ending with `.__code__`):
   - Both raw code and compiled versions are stored
   - Existing contracts are updated if they already exist
   - New contracts are properly registered in the contracts table

4. **Query Support**: The BDS provides methods to query state patches:
   - `get_state_patches()` - List all state patches with pagination
   - `get_state_patches_for_block(block_height)` - Get patches for a specific block
   - `get_state_patch_by_hash(patch_hash)` - Get details about a specific patch
   - `get_state_changes_for_patch(patch_hash)` - Get all state changes from a patch

## ABCI Query Endpoint

State patches can be queried directly via the ABCI query interface using:

```
http://localhost:26657/abci_query?path="/state_patches"
```

This endpoint returns the contents of the node's state patches file, allowing:
- Network operators to verify which patches are loaded on specific validators
- Monitoring tools to check for patch consistency across validator nodes
- Dashboards to display the current state of patches in the network
- Easy identification of validators with missing or incorrect patches

The response is a JSON object containing all patches organized by block height, identical to the format in the state patches file.

## Adding New Patches

To add a new state patch:

1. Edit the `state_patches.json` file to include the new patch
2. Ensure all patches are properly documented with comments
3. Use appropriate future block heights that have not yet been processed
4. Restart the node to load the updated patches

## Security Considerations

- Only network administrators should have access to modify state patches
- All patches should be thoroughly tested in a staging environment before deployment
- Patches should be reviewed by multiple people before being applied
- The comment field should contain sufficient detail for audit purposes

## Validator Consensus Requirements

For state patches to be properly implemented, a quorum of validators must be running the same version of the state patches file. This represents explicit agreement among validators that these state changes should be applied.

- A state patch is considered accepted when a majority (2/3+) of validators by voting power run nodes with the same patch file
- Running a specific version of state patches serves as a signal that validators agree with the changes
- If a majority of validators are not running the same state patches, this indicates a lack of agreement among validators about the implementation
- In case of disagreement, validators should coordinate off-chain to reach consensus before implementing patches
- Network operators should verify validator agreement before deploying critical state patches 