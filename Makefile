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
	cd ./xian-core/contracting && git pull && cd ../..
	git pull
