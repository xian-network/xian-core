# Use Ubuntu 22.04 as base image
FROM ubuntu:22.04

# Install necessary packages
RUN apt-get update \
    && apt-get install -y pkg-config python3.11 python3.11-dev python3.11-venv libhdf5-dev build-essential git wget \
    && rm -rf /var/lib/apt/lists/*

# Clone Xian and related repositories
RUN git clone https://github.com/xian-network/xian-core.git /xian \
    && cd /xian \
    && git clone https://github.com/XianChain/contracting.git

# Set up Python virtual environment and dependencies
RUN python3.11 -m venv /xian_venv \
    && . /xian_venv/bin/activate \
    && pip install -e /xian/contracting/ -e /xian/

# Set the working directory
WORKDIR /xian

# Download, unpack, and initialize Tendermint
RUN wget https://github.com/cometbft/cometbft/releases/download/v0.38.6/cometbft_0.38.6_linux_amd64.tar.gz && \
    tar -xf cometbft_0.38.6_linux_amd64.tar.gz && \
    rm cometbft_0.38.6_linux_amd64.tar.gz && \
    mv cometbft /usr/local/bin && \
    cometbft init

# Expose the Tendermint RPC port
EXPOSE 26657

# Copy the script to the container
COPY start_node.sh /start_node.sh

# Make the script executable
RUN chmod +x /start_node.sh

# Run the script when the container starts
CMD ["/start_node.sh"]
