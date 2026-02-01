wipe:
	rm -rf ~/.cometbft/xian
	../cometbft unsafe-reset-all

up:
	@pm2 delete xian 2>/dev/null || true
	@pm2 delete cometbft 2>/dev/null || true
	cd ./src/xian && pm2 start xian_abci.py --name xian
	pm2 start "../cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft

up-bds:
	@pm2 delete simulator 2>/dev/null || true
	@pm2 delete xian 2>/dev/null || true
	@pm2 delete cometbft 2>/dev/null || true
	cd ./src/xian/services/ && pm2 start simulator.py --name simulator --wait-ready
	cd ./src/xian && pm2 start xian_abci.py --name xian
	pm2 start "../cometbft node --rpc.laddr tcp://0.0.0.0:26657" --name cometbft

logs:
	pm2 logs --lines 1000

down:
	pm2 stop all
	sleep 5  # Give Loguru time to handle any final cleanup
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
	
ex-state:
	python ./src/xian/tools/export_state.py