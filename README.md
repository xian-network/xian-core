# Xian

ABCI application to be used with CometBFT 0.38.7

## Installation

### Ubuntu 22.04

Follow these steps to set up the environment on Ubuntu 22.04:

1. **Update and prepare the system:**

   ```bash
   sudo apt-get update
   sudo apt-get update
   ```

2. **Install necessary packages:**

   ```bash
   sudo apt-get install pkg-config libhdf5-dev build-essential
   ```

3. **Install Python 3.11.8**

   Use your preferred way of installing this.

4. **Clone Xian and related repositories:**

   ```bash
   git clone https://github.com/xian-network/xian-core.git
   cd xian-core
   git clone https://github.com/xian-network/xian-contracting.git
   ```

5. **Set up Python virtual environment and dependencies:**

   ```bash
   python3.11 -m venv xian_venv
   source xian_venv/bin/activate
   pip install -e xian-contracting/ -e .
   ```

6. **Download, unpack, and initialize CometBFT:**

   ```bash
   wget https://github.com/cometbft/cometbft/releases/download/v0.38.7/cometbft_0.38.7_linux_amd64.tar.gz
   tar -xf cometbft_0.38.7_linux_amd64.tar.gz
   rm cometbft_0.38.7_linux_amd64.tar.gz
   ./cometbft init
   ```

7. **Configuring your node:**

   - **For starting your own local network:**

     ```bash
     python src/xian/tools/configure.py --moniker "Node" --copy-genesis True --genesis-file-name genesis.json --validator-privkey "cd6cc45ffe7cebf09c6c6025575d50bb42c6c70c07e1dbc5150aaadc98705c2b"
     ```

     The `--validator-privkey` flag should be set to your validator's private key. The example above uses a key from the genesis file for testing purposes so you can start developing directly. `--moniker` is the node name in the CometBFT network.

   - **For joining an existing network:**

     ```bash
     python src/xian/tools/configure.py --moniker "Node" --copy-genesis True --genesis-file-name genesis-testnet.json --seed-node "91.108.112.184" --validator-privkey "ENTER YOUR WALLET PRIVATE KEY HERE"
     ```

     Use `--seed-node` to specify the seed node's IP address you want to connect to. `--validator-privkey` is your validator wallet's private key. Ensure ports 26657 (REST API), 26656 (Node Communication), and 26660 (Prometheus Metrics) are open on your firewall.

8. **Run CometBFT and Xian:**

   Run CometBFT:

   ```bash
   ./cometbft node --rpc.laddr tcp://0.0.0.0:26657
   ```

   In a new terminal session (remember to activate the environment again with `source xian_venv/bin/activate`), run Xian:

   ```bash
   python src/xian/xian_abci.py
   ```

   Alternatively, use `screen` or install PM2 to manage processes:

   ```bash
   sudo apt-get install npm
   npm install pm2 -g
   make up # To start
   make down # To stop
   ```
   
#### Accessing the Application

CometBFT RPC is exposed on `localhost:26657`.
Xian is running inside the container and can be accessed accordingly.
