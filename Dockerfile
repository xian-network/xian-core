# Use Ubuntu 22.04 as base image
FROM ubuntu:22.04

# Install necessary packages
RUN apt-get update \
    && apt-get install -y pkg-config python3.11 python3.11-dev python3.11-venv libhdf5-dev build-essential git wget \
    && rm -rf /var/lib/apt/lists/*

# Clone Xian and related repositories
RUN git clone https://github.com/XianChain/xian.git /xian \
    && cd /xian \
    && git clone https://github.com/XianChain/contracting.git \
    && git clone https://github.com/XianChain/lamden.git

# Set up Python virtual environment and dependencies
RUN python3.11 -m venv /xian_venv \
    && . /xian_venv/bin/activate \
    && pip install -e /xian/contracting/ -e /xian/lamden/ -e /xian/

# Download, unpack, and initialize Tendermint
RUN wget https://github.com/tendermint/tendermint/releases/download/v0.34.24/tendermint_0.34.24_linux_amd64.tar.gz \
    && tar -xf tendermint_0.34.24_linux_amd64.tar.gz \
    && rm tendermint_0.34.24_linux_amd64.tar.gz \
    && ./tendermint init

# Expose the Tendermint RPC port
EXPOSE 26657

# Set the working directory
WORKDIR /xian

# Command to run Tendermint and Xian
CMD ./tendermint node --rpc.laddr tcp://0.0.0.0:26657 & python3.11 src/xian/xian_abci.py
