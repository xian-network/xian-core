# Default variables
XIAN_CORE_BRANCH := master
CONTRACTING_BRANCH := master

wipe:
	rm -rf ~/.cometbft

up:
	cd ./src/xian && pm2 start xian_abci.py
	pm2 start "./cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft
	pm2 logs --lines 1000

down:
	pm2 delete cometbft xian_abci

restart:
	make down
	make up

node-id:
	./cometbft show-node-id

pull:
	cd ./xian-core/contracting && git checkout $(CONTRACTING_BRANCH) git pull && cd ../..
	git checkout $(XIAN_CORE_BRANCH) && git pull

.PHONY: update_system install_packages clone_repos setup_venv download_cometbft configure_node_local install test dev clean wipe up down restart init node-id dwu pull pull-and-install

update_system:
	sudo apt-get update
	sudo add-apt-repository ppa:deadsnakes/ppa -y
	sudo apt-get update

install_packages:
	sudo apt-get install pkg-config python3.11 python3.11-dev python3.11-venv libhdf5-dev build-essential

clone_repos:
	git clone https://github.com/xian-network/xian-core.git
	cd xian-core && git clone https://github.com/xian-network/contracting.git

setup_venv:
	cd xian-core && python3.11 -m venv xian_venv
	cd xian-core && source xian_venv/bin/activate && pip install -e contracting/ -e .

download_cometbft:
	wget https://github.com/cometbft/cometbft/releases/download/v0.38.6/cometbft_0.38.6_linux_amd64.tar.gz
	tar -xf cometbft_0.38.6_linux_amd64.tar.gz
	rm cometbft_0.38.6_linux_amd64.tar.gz
	./cometbft init

configure_node_local:
	cd xian-core && source xian_venv/bin/activate && python src/xian/tools/configure.py --moniker "Node" --copy-genesis True --genesis-file-name genesis.json --validator-privkey "cd6cc45ffe7cebf09c6c6025575d50bb42c6c70c07e1dbc5150aaadc98705c2b"

install: update_system install_packages clone_repos setup_venv download_cometbft configure_node_local
	@echo "Installation and setup for local node completed. Use 'make up' to start the node and 'make down' to stop it."

test:
	pytest .

dev:
	cd xian-core && source xian_venv/bin/activate && pip install --editable '.[dev]'

clean:
	@rm -Rf dist/

wipe:
	rm -rf ~/.cometbft/xian
	./cometbft unsafe-reset-all

up:
	cd ./src/xian && pm2 start xian_abci.py
	pm2 start "./cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft
	pm2 logs --lines 1000

down:
	pm2 delete cometbft xian_abci

restart:
	make down
	make up

init:
	./cometbft init

node-id:
	./cometbft show-node-id

dwu:
	make down
	make wipe
	make init
	make up

pull:
	cd ./xian-core/contracting && git pull && cd ../..
	git pull

pull-and-install:
	make pull
	make install
