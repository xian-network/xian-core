import json
import sys


def update_json(genesis_file_path, json_data_file_path):
    with open(genesis_file_path, 'r') as file:
        cometbft_genesis = json.load(file)

    with open(json_data_file_path, 'r') as file:
        abci_genesis = json.load(file)

    cometbft_genesis['abci_genesis'] = abci_genesis
    cometbft_genesis['initial_height'] = str(abci_genesis["number"])

    with open(genesis_file_path, 'w') as file:
        json.dump(cometbft_genesis, file, indent=4)


if __name__ == "__main__":
    genesis_file_path = sys.argv[1]
    json_data_file_path = sys.argv[2]
    update_json(genesis_file_path, json_data_file_path)
