wipe:
	rm -rf ~/.cometbft

up:
	make pull
	pm2 start src/xian/xian_abci.py
	pm2 start "./cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft
	pm2 logs --lines 1000

down:
	pm2 delete cometbft xian_abci

restart:
	make down
	make up

reset-local:
	rm -rf ~/.cometbft
	./cometbft init
	python3.11 src/xian/tools/configure.py --moniker "${moniker}" --copy-genesis True --genesis-file-name genesis.json --validator-privkey "cd6cc45ffe7cebf09c6c6025575d50bb42c6c70c07e1dbc5150aaadc98705c2b"

reset-testnet-join:
	rm -rf ~/.cometbft
	./cometbft init
	python3.11 src/xian/tools/configure.py --moniker "${moniker}" --copy-genesis True --genesis-file-name genesis-testnet.json --validator-privkey "${private_key}" --seed-node "testnet.xian.org"

reset-testnet-create:
	rm -rf ~/.cometbft
	./cometbft init
	python3.11 src/xian/tools/configure.py --moniker "${moniker}" --copy-genesis True --genesis-file-name genesis-testnet.json --validator-privkey "${private_key}"

pull:
	cd contracting && git pull && cd ../..
	git pull
