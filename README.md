# Xian
ABCI application to be used with CometBFT 0.38.6

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
    git clone https://github.com/xian-network/xian-core.git
    cd xian
    git clone https://github.com/XianChain/contracting.git
    ```

4. Set up Python virtual environment and dependencies:
    ```
    python3.11 -m venv xian_venv
    source xian_venv/bin/activate
    pip install -e contracting/ -e .
    ```

5. Download, unpack, and initialize CometBFT:
    ```
    wget https://github.com/cometbft/cometbft/releases/download/v0.38.6/cometbft_0.38.6_linux_amd64.tar.gz
    tar -xf cometbft_0.38.6_linux_amd64.tar.gz
    rm cometbft_0.38.6_linux_amd64.tar.gz
    ./cometbft init
    cp src/xian/genesis/genesis.json /root/.cometbft/config/genesis.json
    cp src/xian/config/config.toml /root/.cometbft/config/config.toml
    rm /root/.cometbft/config/node_key.json
    rm /root/.cometbft/config/priv_validator_key.json
    echo '{"address": "ee06a34cf08bf72ce592d26d36b90c79daba2829ba9634992d034318160d49f9", "pub_key": {"type": "tendermint/PubKeyEd25519", "value": "7gajTPCL9yzlktJtNrkMedq6KCm6ljSZLQNDGBYNSfk="}, "priv_key": {"type": "tendermint/PrivKeyEd25519", "value": "zWzEX/586/CcbGAlV11Qu0LGxwwH4dvFFQqq3JhwXCvuBqNM8Iv3LOWS0m02uQx52rooKbqWNJktA0MYFg1J+Q=="}}' > /root/.cometbft/config/priv_validator_key.json
    ./cometbft node --rpc.laddr tcp://0.0.0.0:26657
    ```

6. Run Xian:
    ```
   (If in a separate terminal session, don't forget to use: "source xian_venv/bin/activate" again)
    python src/xian/xian_abci.py
    ```

Either run step 5 and 6 in separate sessions and let the applications run in the background with the help of the `screen` command or install PM2 with:
```
sudo apt-get install npm
npm install pm2 -g
```


Then start cometbft node and xian_acbi with:
```
make up
```

And stop cometbft node and xian_acbi with:
```
make down
```

### Docker

This is currently not updated.

#### Prerequisites

Docker and Docker Compose must be installed on your system. See [Docker documentation](https://docs.docker.com/get-docker/) for instructions.

#### Steps

Clone the Xian repository:

```
git clone https://github.com/xian-network/xian-core.git
cd xian
```

Build and run the Docker container:

```
docker-compose up --build
```

This command builds the Docker image according to the Dockerfile in the repository and starts the container. The CometBFT node and Xian application will run inside this container.

#### Accessing the Application

CometBFT RPC is exposed on `localhost:26657`.
Xian is running inside the container and can be accessed accordingly.

## API Endpoints Documentation

This section documents the available API endpoints for querying the application state and interacting with transactions. Each query and transaction request is made to the cometbft RPC interface with specific paths to interact with the application.

### Query Application State

- **Endpoint**: `/abci_query`
- **Method**: GET
- **Base URL**: `http://89.163.130.217:26657`

#### Query Examples

1. **Query Specific Path**

   To query a specific path within the application, you must include the path parameter in the query string. Note that the path value should be URL-encoded and wrapped in quotes.

   - **Request Example**: `/abci_query?path="path"`

     Replace `"path"` with the actual path you want to query. 

2. **Get Value of a Key**

   Queries the value of a specified key from the application's state.

   - **Request Example**: `/abci_query?path="/get/currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"`

3. **Check Health**

   Returns the health status of the application.

   - **Request Example**: `/abci_query?path="/health"`

     Expected response: `"OK"`

4. **Get Next Nonce**

   Fetches the next nonce for a given sender.

   - **Request Example**: `/abci_query?path="/get_next_nonce/ddd326fddb5d1677595311f298b744a4e9f415b577ac179a6afbf38483dc0791"`

### Broadcast Transaction

- **Endpoint**: `/broadcast_tx_commit`
- **Method**: POST
- **Base URL**: `http://89.163.130.217:26657`
- **Description**: Submits a transaction to be processed by the network.

#### Broadcast Transaction Example

   - **Request Example**: 

     ```
     POST /broadcast_tx_commit?tx="{payload}"
     ```

     Where `{payload}` is a hex-encoded string representing the transaction data. The transaction data includes metadata such as the signature and timestamp, along with the payload containing the contract information, function to be called, arguments (`kwargs`), nonce, sender, and stamps supplied.

### Get Transaction

- **Endpoint**: `/tx`
- **Method**: GET
- **Base URL**: `http://89.163.130.217:26657`
- **Description**: Retrieves details of a transaction by its hash.

#### Get Transaction Example

   - **Request Example**: 

     ```
     GET /tx?hash=0x{tx_hash}
     ```

     Replace `{tx_hash}` with the actual transaction hash to retrieve its details.

#### Response Structure

Responses for querying the application state, broadcasting transactions, and retrieving transaction details will contain either the requested information or an error message. In case of an error, a log with the error message will be included.

- **Success Response for Query**: `ResponseQuery(code=OkCode, value=v)`
- **Success Response for Transaction Actions**: JSON object containing transaction details or result.
- **Error Response**: `ResponseQuery(code=ErrorCode, log="QUERY ERROR")` or relevant error message in JSON format for transaction actions.

Ensure that all paths, JSON objects in your queries, and transaction data are correctly formatted and URL-encoded to avoid errors.
