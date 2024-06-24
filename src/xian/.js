const XianWalletUtils = {
    rpcUrl: 'https://testnet.xian.org', // Default RPC URL
    isWalletReady: false,
    walletReadyResolver: null,

    hexToString: function(hex) {
        // Convert hex string to bytes
        let bytes = [];
        for (let i = 0; i < hex.length; i += 2) {
            bytes.push(parseInt(hex.substr(i, 2), 16));
        }

        // Convert bytes to string
        return String.fromCharCode.apply(String, bytes);
    },

    // Initialize listeners to resolve promises and set RPC URL
    init: function(rpcUrl) {
        if (rpcUrl) {
            this.rpcUrl = rpcUrl;
        }

        document.addEventListener('xianWalletInfo', event => {
            if (this.walletInfoResolver) {
                this.walletInfoResolver(event.detail);
                this.walletInfoResolver = null; // Reset the resolver after use
            }
        });

        document.addEventListener('xianWalletTxStatus', event => {
            if (this.transactionResolver) {
                if ('errors' in event.detail) {
                    this.transactionResolver(event.detail);
                    this.transactionResolver = null; // Reset the resolver after use
                    return;
                }
                this.getTxResultsAsyncBackoff(event.detail.txid).then(tx => {
                    let data = tx.result.tx_result.data;
                    let original_tx = tx.result.tx
                    let decodedData = window.atob(data);
                    let decodedOriginalTx = window.atob(original_tx);
                    let parsedData = JSON.parse(decodedData);
                    parsedData.original_tx = JSON.parse(this.hexToString(decodedOriginalTx));
                    this.transactionResolver(parsedData);
                    this.transactionResolver = null; // Reset the resolver after use
                }).catch(error => {
                    console.error('Final error after retries:', error);
                    this.transactionResolver(null);
                });
            }
        });

        document.addEventListener('xianReady', () => {
            this.isWalletReady = true;
            if (this.walletReadyResolver) {
                this.walletReadyResolver();
                this.walletReadyResolver = null; // Reset the resolver after use
            }
            console.log('Xian Wallet is ready');
        });
    },

    waitForWalletReady: function() {
        return new Promise(resolve => {
            if (this.isWalletReady) {
                resolve();
            } else {
                this.walletReadyResolver = resolve;
                setTimeout(() => {
                    if (!this.isWalletReady) {
                        this.walletReadyResolver = null; // Clear the resolver
                        resolve(); // Resolve anyway to not block the flow
                    }
                }, 2000); // 2 seconds timeout
            }
        });
    },

    // Request wallet information and return a promise that resolves with the info
    requestWalletInfo: async function() {
        await this.waitForWalletReady();
        return new Promise((resolve, reject) => {
            this.walletInfoResolver = resolve; // Store the resolver to use in the event listener

            // Set a timeout to reject the promise if it does not resolve within a certain timeframe
            const timeoutId = setTimeout(() => {
                this.walletInfoResolver = null; // Clear the resolver
                reject(new Error('Xian Wallet Chrome extension not installed or not responding'));
            }, 2000); // 2 seconds timeout

            // Dispatch the event to request wallet info
            document.dispatchEvent(new CustomEvent('xianWalletGetInfo'));

            // Wrap the original resolve to clear the timeout when resolved
            this.walletInfoResolver = (info) => {
                clearTimeout(timeoutId);
                resolve(info);
            };
        });
    },

    // Send a transaction with detailed parameters and return a promise that resolves with the transaction status
    sendTransaction: async function(contract, method, kwargs) {
        await this.waitForWalletReady();
        return new Promise((resolve, reject) => {
            this.transactionResolver = resolve; // Store the resolver to use in the event listener
            document.dispatchEvent(new CustomEvent('xianWalletSendTx', {
                detail: {
                    contract: contract,
                    method: method,
                    kwargs: kwargs
                }
            }));

            // Set a timeout to reject the promise if it does not resolve within a certain timeframe
            const timeoutId = setTimeout(() => {
                this.transactionResolver = null; // Clear the resolver
                reject(new Error('Xian Wallet Chrome extension not responding'));
            }, 30000); // 30 seconds timeout, this requires manual confirmation

            // Wrap the original resolve to clear the timeout when resolved
            this.transactionResolver = (txStatus) => {
                clearTimeout(timeoutId);
                resolve(txStatus);
            };
        });
    },

    getTxResults: async function(txHash) {
        try {
            const response = await fetch(`${this.rpcUrl}/tx?hash=0x${txHash}`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.log('Transaction not found yet');
            throw error; // Rethrow the error to trigger retries
        }
    },

    getBalanceRequest: async function(address, contract) {
        const response = await fetch(`${this.rpcUrl}/abci_query?path=%22/get/${contract}.balances:${address}%22`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        let balance = data.result.response.value;
        if (balance === 'AA==') {
            return 0;
        }
        let decodedBalance = window.atob(balance);
        return decodedBalance;
    },

    getBalance: async function(contract) {
        const info = await this.requestWalletInfo();
        const address = info.address;
        const balance = await this.getBalanceRequest(address, contract);
        return balance;
    },

    getApprovedBalanceRequest: async function(token_contract, address, approved_to) {
        const response = await fetch(`${this.rpcUrl}/abci_query?path=%22/get/${token_contract}.balances:${address}:${approved_to}%22`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        let balance = data.result.response.value;
        if (balance === 'AA==') {
            return 0;
        }
        let decodedBalance = window.atob(balance);
        return decodedBalance;
    },

    getApprovedBalance: async function(token_contract, approved_to) {
        const info = await this.requestWalletInfo();
        const address = info.address;
        const balance = await this.getApprovedBalanceRequest(token_contract, address, approved_to);
        return balance;
    },

    getTxResultsAsyncBackoff: async function(txHash, retries = 5, delay = 1000) {
        try {
            return await this.getTxResults(txHash);
        } catch (error) {
            if (retries === 0) {
                throw error;
            }
            await new Promise(resolve => setTimeout(resolve, delay));
            return await this.getTxResultsAsyncBackoff(txHash, retries - 1, delay * 2);
        }
    }
};

