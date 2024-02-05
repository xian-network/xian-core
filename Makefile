# Origin
version_branch = v0.34.24
tendermint = https://raw.githubusercontent.com/tendermint/tendermint/$(version_branch)

# Outputs
tmabci = protos/tendermint/abci/types.proto
tmtypes =  protos/tendermint/types/types.proto
tmpubkey = protos/tendermint/crypto/keys.proto
tmproof =  protos/tendermint/crypto/proof.proto
tmparams = protos/tendermint/types/params.proto
tmversions =  protos/tendermint/version/types.proto
tmvalidator = protos/tendermint/types/validator.proto

# Only run this to rebuild/update protobufs from the tendermint source
update-proto:
	curl $(tendermint)/proto/tendermint/abci/types.proto > $(tmabci)
	curl $(tendermint)/proto/tendermint/crypto/keys.proto > $(tmpubkey)
	curl $(tendermint)/proto/tendermint/crypto/proof.proto > $(tmproof)
	curl $(tendermint)/proto/tendermint/types/params.proto > $(tmparams)
	curl $(tendermint)/proto/tendermint/types/types.proto > $(tmtypes)
	curl $(tendermint)/proto/tendermint/types/validator.proto > $(tmvalidator)
	curl $(tendermint)/proto/tendermint/version/types.proto > $(tmversions)
	curl $(tendermint)/version/version.go | grep -F -eTMVersionDefault -eABCISemVer > tm_version.txt
	@python build_proto.py

test_tm:
	@rm -Rf .test_pyabci
	@tendermint --home .test_pyabci init
	@tendermint --home .test_pyabci node

test:
	pytest .

dev:
	pip install --editable '.[dev]'

clean:
	@rm -Rf dist/

# PyPi package deploy:
# 1. build-dist
# 2. test-pypi
# 3. update-pypi
build-dist:
	python -m build

publish-test:
	twine upload dist/* --repository testpypi

publish:
	twine upload dist/* --repository pypi

rc:
	cp ~/.tendermint/xian ~/.tendermint/xian_last -r
	rm -rf ~/.tendermint/xian

wipe:
	rm -rf ~/.tendermint/xian
	./tendermint unsafe-reset-all

up:
	cd ./src/xian && pm2 start xian_abci.py
	pm2 start "./tendermint node" --name tendermint
	pm2 logs --lines 1000

down:
	pm2 delete all

r:
	make down
	make up
