# Xian
ABCI application to be used with Tendermint

## Installation
### Ubuntu 22.04

Follow these steps to set up the environment on Ubuntu 22.04:

1. Update the package list:
    ```
    sudo apt-get update
    ```

2. Add the Deadsnakes PPA for Python 3.11:
    ```
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    ```

3. Update the package list again:
    ```
    sudo apt-get update
    ```

4. Install pkg-config:
    ```
    sudo apt-get install pkg-config
    ```

5. Install Python 3.11:
    ```
    sudo apt-get install python3.11
    ```

6. Install Python 3.11 development package:
    ```
    sudo apt-get install python3.11-dev
    ```

7. Install Python 3.11 venv package:
    ```
    sudo apt-get install python3.11-venv
    ```

8. Install libhdf5 development package:
    ```
    sudo apt-get install libhdf5-dev
    ```

9. Install build-essential package:
    ```
    sudo apt-get install build-essential
    ```

10. Clone the Xian repository:
    ```
    git clone https://github.com/XianChain/xian.git
    ```

11. Change directory to the cloned repository:
    ```
    cd xian
    ```

12. Clone the XianChain contracting and lamden repositories:
    ```
    git clone https://github.com/XianChain/contracting.git
    git clone https://github.com/XianChain/lamden.git
    ```

13. Create a Python virtual environment and activate it:
    ```
    python3.11 -m venv xian_venv
    source xian_venv/bin/activate
    ```

14. Install dependencies using pip:
    ```
    pip install -e contracting/
    pip install -e lamden/
    pip install -e .
    ```

15. Download and unpack Tendermint:
    ```
    wget https://github.com/tendermint/tendermint/releases/download/v0.34.24/tendermint_0.34.24_linux_amd64.tar.gz
    tar -xf tendermint_0.34.24_linux_amd64.tar.gz
    rm tendermint_0.34.24_linux_amd64.tar.gz
    ```

16. Initialize and run Tendermint:
    ```
    ./tendermint init
    ./tendermint node --rpc.laddr tcp://0.0.0.0:26657
    ```
