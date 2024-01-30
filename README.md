# Xian
ABCI application to be used with Tendermint

## Installation
### Ubuntu 22.04

Set up the environment on Ubuntu 22.04 with the following steps:

1. Update and prepare the system:
    ```
    sudo apt-get update
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt-get update
    ```

2. Install necessary packages:
    ```
    sudo apt-get install pkg-config python3.11 python3.11-dev python3.11-venv libhdf5-dev build-essential
    ```

3. Clone Xian and related repositories:
    ```
    git clone https://github.com/XianChain/xian.git
    cd xian
    git clone https://github.com/XianChain/contracting.git
    git clone https://github.com/XianChain/lamden.git
    ```

4. Set up Python virtual environment and dependencies:
    ```
    python3.11 -m venv xian_venv
    source xian_venv/bin/activate
    pip install -e contracting/ -e lamden/ -e .
    ```

5. Download, unpack, and initialize Tendermint:
    ```
    wget https://github.com/tendermint/tendermint/releases/download/v0.34.24/tendermint_0.34.24_linux_amd64.tar.gz
    tar -xf tendermint_0.34.24_linux_amd64.tar.gz
    rm tendermint_0.34.24_linux_amd64.tar.gz
    ./tendermint init
    ./tendermint node --rpc.laddr tcp://0.0.0.0:26657
    ```

6. Run Xian:
    ```
    python3.11 src/xian/xian_abci.py
    ```