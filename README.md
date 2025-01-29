# Xian Core

[![CI](https://github.com/xian-network/xian-core/actions/workflows/main.yml/badge.svg)](https://github.com/xian-network/xian-core/actions/workflows/main.yml)

Python-based ABCI (Application Blockchain Interface) server designed for CometBFT 0.38.12. This component serves as the core application layer for the Xian blockchain network.

## Requirements

- Python 3.11 (other versions are not supported)
- CometBFT 0.38.12
- PostgreSQL (for Blockchain Data Service)
- PM2 (for process management)

## Key Features

- **ABCI Server**: Full implementation of CometBFT's ABCI protocol
- **Smart Contract Support**: Execution environment for Python-based smart contracts
- **State Management**: Advanced state handling with Hash and Variable storage types
- **Transaction Processing**: Comprehensive transaction validation and execution
- **Event System**: Rich event logging system for tracking contract and state changes
- **Blockchain Data Service (BDS)**: PostgreSQL-based service for storing and querying blockchain data
- **Validator Management**: Flexible validator set management
- **Rewards System**: Built-in system for handling transaction fees and rewards
- **Process Monitoring**: PM2-based process management

## Installation

```bash
# Install the package
pip install xian-core
```

## Basic Usage

### Starting the Node

```bash
# Initialize CometBFT
make init

# Start Xian ABCI and CometBFT
make up

# View logs
make logs

# Stop all services
make down
```

### Advanced Commands

```bash
# Wipe and restart
make dwu  # (down, wipe, init, up)

# Start with simulator
make up-bds

# Get node ID
make node-id

# Export state
make ex-state
```

## Configuration

The node uses several configuration files:

- CometBFT configuration: `~/.cometbft/config/config.toml`
- Genesis file: `~/.cometbft/config/genesis.json`
- BDS configuration: Located in the BDS service directory

## Blockchain Data Service

The BDS provides persistent storage and querying capabilities:

- Transaction history
- State changes
- Contract deployments
- Events and rewards
- Address tracking

### Query Examples

```bash
# Get contract state
curl "http://localhost:26657/abci_query?path=\"/get/currency.balances:ADDRESS\""

# Get node health
curl "http://localhost:26657/abci_query?path=\"/health\""

# Get next nonce
curl "http://localhost:26657/abci_query?path=\"/get_next_nonce/ADDRESS\""
```

## Architecture Components

- **ABCI Server**: Handles communication with CometBFT
- **Transaction Processor**: Manages transaction execution and state updates
- **Validator Handler**: Manages validator set changes
- **Rewards Handler**: Processes transaction fees and rewards
- **Nonce Manager**: Handles transaction ordering
- **Event System**: Tracks and logs blockchain events

## Development

To set up a development environment:

```bash
# Clone the repository
git clone https://github.com/xian-network/xian-core.git

# Install dependencies
pip install -e .

# Run tests
python -m pytest tests/
```

## License

This project is licensed under the Apache License Version 2.0 - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [xian-contracting](https://github.com/xian-network/xian-contracting): Smart contract engine
- [xian-stack](https://github.com/xian-network/xian-stack): Complete blockchain stack deployment
