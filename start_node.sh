#!/bin/bash

# Activate the Python virtual environment
source /xian_venv/bin/activate

# Start Tendermint
tendermint node --rpc.laddr tcp://0.0.0.0:26657 &

# Start Xian
python /xian/src/xian/xian_abci.py
