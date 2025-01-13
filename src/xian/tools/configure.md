# Xian Configuration Tool

A unified configuration tool for Xian nodes that handles both genesis file generation and node configuration. This tool provides a streamlined way to:
- Generate genesis files for new networks
- Configure CometBFT nodes
- Perform both operations in a single command

## Prerequisites

- Python 3.8 or higher
- Xian Core installed
- CometBFT installed

Required Python packages:
```bash
pip install requests toml contracting nacl
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/your-repo/xian-config.git
cd xian-config
```

2. Make the script executable:
```bash
chmod +x xian_config.py
```

## Usage

The tool operates in three modes:
- `genesis`: Only generates genesis files
- `node`: Only configures the node
- `full`: Performs both genesis generation and node configuration

### Command Line Options

```
Required Arguments (depending on mode):
  --mode {genesis,node,full}   Operation mode
  --founder-privkey KEY       Founder's private key (required for genesis/full)
  --validator-privkey KEY     Validator's private key (required for node/full)
  --moniker NAME             Node name (required for node/full)

Optional Arguments:
  --chain-id ID              Chain ID for the network (default: xian-network)
  --network TYPE             Network type (default: devnet)
  --genesis-path PATH        Custom path for genesis file
  --single-node             Set all contracts to be owned by founder
  --seed-node IP            Seed node IP address
  --seed-node-address ADDR  Full seed node address
  --allow-cors              Enable CORS (default: true)
  --snapshot-url URL        URL of node snapshot
  --service-node            Run as a service node
  --enable-pruning          Enable block pruning
  --blocks-to-keep NUM      Number of blocks to keep when pruning (default: 100000)
  --prometheus              Enable Prometheus metrics (default: true)
```

### Example Commands

1. **Generate Genesis File Only**:
```bash
# Basic genesis generation
python3 xian_config.py \
  --mode genesis \
  --founder-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Genesis with single-node and custom chain ID
python3 xian_config.py \
  --mode genesis \
  --founder-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --single-node \
  --chain-id my-testnet-1 \
  --network testnet

# Genesis with custom output path
python3 xian_config.py \
  --mode genesis \
  --founder-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --genesis-path /path/to/output \
  --network devnet
```

2. **Configure Node Only**:
```bash
# Basic node configuration
python3 xian_config.py \
  --mode node \
  --validator-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --moniker "my-validator-node"

# Node with seed configuration
python3 xian_config.py \
  --mode node \
  --validator-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --moniker "my-validator-node" \
  --seed-node 91.108.112.184 \
  --chain-id my-testnet-1

# Service node with pruning enabled
python3 xian_config.py \
  --mode node \
  --validator-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --moniker "service-node" \
  --service-node \
  --enable-pruning \
  --blocks-to-keep 50000
```

3. **Full Setup (Genesis + Node Configuration)**:
```bash
# Basic full setup
python3 xian_config.py \
  --mode full \
  --founder-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --validator-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --moniker "my-node"

# Full setup for a single-node testnet
python3 xian_config.py \
  --mode full \
  --founder-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --validator-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --moniker "single-node" \
  --single-node \
  --chain-id my-testnet-1 \
  --network testnet

# Full setup with all options
python3 xian_config.py \
  --mode full \
  --founder-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --validator-privkey 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --moniker "full-node" \
  --chain-id my-chain \
  --network testnet \
  --single-node \
  --service-node \
  --enable-pruning \
  --blocks-to-keep 50000 \
  --prometheus \
  --allow-cors \
  --snapshot-url https://example.com/snapshot.tar.gz
```

## Important Notes

1. Ensure CometBFT is initialized before running node configuration:
```bash
cometbft init
```

2. Required ports:
   - 26656: P2P communication
   - 26657: RPC API

3. When using `--single-node`, all contracts will be owned by the founder's account.

4. The `genesis` mode creates files in the specified output directory or `./genesis/` by default.

5. Node configuration files are stored in `~/.cometbft/`.

## Directory Structure

```
.
├── configure.py           # Main configuration script
└── genesis/               # Default directory for genesis files
    └── contracts/         # Contract files for genesis generation
        ├── contracts_devnet.json
        ├── contracts_testnet.json
        └── ...            # Contract source files
```

## Error Handling

The tool includes comprehensive error handling:
- Validates required arguments based on the selected mode
- Provides clear error messages for missing prerequisites
- Handles network and file system errors gracefully

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)