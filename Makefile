wipe:
	rm -rf ~/.cometbft/xian
	../cometbft unsafe-reset-all

up:
	cd ./src/xian && pm2 start xian_abci.py --name xian -f
	pm2 start "../cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft -f

up-bds:
	cd ./src/xian/services/ && pm2 start stamp_calculator.py --name stamp_calculator -f --wait-ready
	cd ./src/xian && pm2 start xian_abci.py --name xian -f
	pm2 start "../cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft -f

logs:
	pm2 logs --lines 1000

down:
	pm2 delete all

restart:
	make down
	make up

init:
	../cometbft init

node-id:
	../cometbft show-node-id

dwu:
	make down
	make wipe
	make init
	make up

pull-and-install:
	make pull
	make install
