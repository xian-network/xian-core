# Check for required tools
REQUIRED_TOOLS := pm2 python
$(foreach tool,$(REQUIRED_TOOLS),\
    $(if $(shell command -v $(tool) 2> /dev/null),,\
        $(error "$(tool) not found in PATH. Please install it.")))

.PHONY: wipe up up-bds logs down restart init node-id dwu ex-state help

# Default target
.DEFAULT_GOAL := help

# Variables for paths
COMETBFT_DIR := ~/.cometbft/xian
XIAN_DIR := ./src/xian

help:
	@echo "Available commands:"
	@echo "  make up        - Start xian node and CometBFT"
	@echo "  make up-bds    - Start with Blockchain Data Service"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - Show logs"
	@echo "  make restart   - Restart all services"
	@echo "  make wipe      - Clean blockchain data"
	@echo "  make init      - Initialize CometBFT"
	@echo "  make node-id   - Show node ID"
	@echo "  make dwu       - Down, wipe, init, up"
	@echo "  make ex-state  - Export state"

wipe:
	@echo "Wiping blockchain data..."
	rm -rf $(COMETBFT_DIR)
	cometbft unsafe-reset-all

up:
	@echo "Starting services..."
	cd $(XIAN_DIR) && pm2 start xian_abci.py --name xian -f
	pm2 start "cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft -f
	@echo "Services started. Use 'make logs' to view logs."

up-bds:
	@echo "Starting services with simulator..."
	cd $(XIAN_DIR)/services/ && pm2 start simulator.py --name simulator -f --wait-ready
	cd $(XIAN_DIR) && pm2 start xian_abci.py --name xian -f
	pm2 start "cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft -f
	@echo "Services started. Use 'make logs' to view logs."

logs:
	pm2 logs --lines 1000

down:
	@echo "Stopping services..."
	-pm2 stop all
	@echo "Waiting for cleanup..."
	sleep 3  # Give Loguru time to handle any final cleanup
	-pm2 delete all
	@echo "Services stopped."

restart: down up

init:
	@echo "Initializing cometbft..."
	cometbft init
	@echo "Initialization complete."

node-id:
	@echo "Node ID:"
	cometbft show-node-id

dwu: down wipe init up
	@echo "Down, wipe, init, up sequence completed."

ex-state:
	python $(XIAN_DIR)/tools/export_state.py