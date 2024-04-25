import json
import sys


def update_json(genesis_file_path, json_data_file_path):
    with open(genesis_file_path, 'r') as file:
        data = json.load(file)

    with open(json_data_file_path, 'r') as file:
        new_data = json.load(file)

    data['abci_genesis'] = new_data

    with open(genesis_file_path, 'w') as file:
        json.dump(data, file, indent=4)


if __name__ == "__main__":
    genesis_file_path = sys.argv[1]
    json_data_file_path = sys.argv[2]
    update_json(genesis_file_path, json_data_file_path)