# Xian Core

[![CI](https://github.com/xian-network/xian-core/actions/workflows/main.yml/badge.svg)](https://github.com/xian-network/xian-core/actions/workflows/main.yml)

Python-based ABCI (Application Blockchain Interface) server designed for CometBFT 0.38.12. This component serves as the core application layer for the Xian blockchain network.

## Requirements

- Python 3.11 (other versions are not supported)
- CometBFT 0.38.12
- PostgreSQL (for Blockchain Data Service)
- PM2 (for process management)

## Installation and Usage

There are two ways to set up and run Xian Core:

### Method 1: Production Installation (via PyPI)

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install the package
pip install xian-core

# Initialize the node
xian init

# Start the node (standard mode)
xian up

# Start the node with Blockchain Data Service (BDS)
xian up --bds

# View logs
xian logs

# Stop the node
xian down
```

Additional commands:
```bash
xian node-id  # Get node ID
xian wipe     # Wipe blockchain data
xian help     # Show all available commands
```

### Method 2: Development Installation (from source)

```bash
# Clone the repository
git clone https://github.com/xian-network/xian-core.git
cd xian-core

# Create and activate a virtual environment
python3.11 -m venv xian-venv
source xian-venv/bin/activate
cd xian-core

# Install in development mode
pip install -e .

# Initialize CometBFT
make init

# Start the node (standard mode)
make up

# Start the node with Blockchain Data Service (BDS)
make up-bds

# View logs
make logs

# Stop all services
make down
```

Additional Makefile commands:
```bash
make dwu       # Down, wipe, init, up sequence
make node-id   # Show node ID
make ex-state  # Export state
```

## Key Features

- **ABCI Server**: Full implementation of CometBFT's ABCI protocol
- **Smart Contract Support**: Execution environment for Python-based smart contracts
- **State Management**: Advanced state handling with Hash and Variable storage types
- **Transaction Processing**: Comprehensive transaction validation and execution
- **Event System**: Rich event logging system for tracking contract and state changes
- **Blockchain Data Service (BDS)**: PostgreSQL-based service for storing and querying blockchain data
- **Validator Management**: Flexible validator set management
- **Rewards System**: Built-in system for handling transaction fees and rewards

## Blockchain Data Service (BDS)

The Blockchain Data Service provides additional data storage and querying capabilities:
- Store blockchain data in a PostgreSQL database
- Enable advanced querying and indexing of blockchain state
- Enhance performance for complex data retrieval

### Starting with BDS

To start the node with the Blockchain Data Service enabled, use:
```bash
# In PyPI installation
xian up --bds

# In development mode
make up-bds
```

## Architecture Components

- **ABCI Server**: Handles communication with CometBFT
- **Transaction Processor**: Manages transaction execution and state updates
- **Validator Handler**: Manages validator set changes
- **Rewards Handler**: Processes transaction fees and rewards
- **Nonce Manager**: Handles transaction ordering
- **Event System**: Tracks and logs blockchain events
- **Blockchain Data Service**: Provides advanced data storage and querying

## Configuration

The node uses several configuration files:

- CometBFT configuration: `~/.cometbft/config/config.toml`
- Genesis file: `~/.cometbft/config/genesis.json`
- BDS configuration: Located in the BDS service directory

## Query Interface

Examples of querying the node:

```bash
# Get contract state
curl "http://localhost:26657/abci_query?path=\"/get/currency.balances:ADDRESS\""

# Get node health
curl "http://localhost:26657/abci_query?path=\"/health\""

# Get next nonce
curl "http://localhost:26657/abci_query?path=\"/get_next_nonce/ADDRESS\""
```

## Development

### Testing
```bash
# Run tests
python -m pytest tests/
```

### Creating a Release
```bash
# Install required tools
pip install poetry

# Create a new release
./release.sh patch  # For bug fixes (0.1.0 -> 0.1.1)
./release.sh minor  # For new features (0.1.0 -> 0.2.0)
./release.sh major  # For breaking changes (0.1.0 -> 2.0.0)
```

## License

This project is licensed under the Apache License Version 2.0 - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [xian-contracting](https://github.com/xian-network/xian-contracting): Smart contract engine
- [xian-stack](https://github.com/xian-network/xian-stack): Complete blockchain stack deployment