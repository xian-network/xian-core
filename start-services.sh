#!/bin/bash

# Start Tendermint
tendermint node --rpc.laddr tcp://0.0.0.0:26657 &

# Start Xian
python3.11 /xian/src/xian/xian_abci.py