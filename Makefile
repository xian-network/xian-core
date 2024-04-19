wipe:
	rm -rf ~/.cometbft/xian
	./cometbft unsafe-reset-all

up:
	cd ./src/xian && pm2 start xian_abci.py --name xian
	pm2 start "./cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft
	pm2 logs --lines 1000

down:
	pm2 delete cometbft xian

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

pull-and-install:
	make pull
	make install
