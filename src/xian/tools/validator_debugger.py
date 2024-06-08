import urwid
import json
import requests
import asyncio
import argparse

class ValidatorDebugger:

    def get_validators(self, seed_node):
        validators = {}
        try:
            # Get the latest block height using status endpoint
            status_response = requests.get(f"http://{seed_node}:26657/status")
            status_response.raise_for_status()
            status_data = status_response.json()
            latest_block_height = status_data["result"]["sync_info"]["latest_block_height"]
            moniker = status_data["result"]["node_info"]["moniker"]
            chain_id = status_data["result"]["node_info"]["network"]

            # Get the validator addresses using validators endpoint and latest block height
            validator_response = requests.get(f"http://{seed_node}:26657/validators?height={latest_block_height}")
            validator_response.raise_for_status()
            validators_data = validator_response.json()

            for validator in validators_data["result"]["validators"]:
                validators[validator["address"]] = {"ip": seed_node, "latest_block_height": latest_block_height, "catching_up": False, "moniker": moniker, "chain_id": chain_id}

            # Get the IP addresses using net_info and use the IP addresses to check if the node is a validator
            net_info_response = requests.get(f"http://{seed_node}:26657/net_info")
            net_info_response.raise_for_status()
            net_info_data = net_info_response.json()

            for peer in net_info_data["result"]["peers"]:
                if "remote_ip" in peer:
                    try:
                        status_validator_response = requests.get(f"http://{peer['remote_ip']}:26657/status", timeout=2)
                        status_validator_response.raise_for_status()
                        status_validator_data = status_validator_response.json()
                        validator_info = status_validator_data["result"]["validator_info"]
                        address = validator_info["address"]
                        if address in validators:
                            validators[address]["ip"] = peer["remote_ip"]
                            validators[address]["latest_block_height"] = status_validator_data["result"]["sync_info"]["latest_block_height"]
                            validators[address]["catching_up"] = status_validator_data["result"]["sync_info"]["catching_up"]
                            validators[address]["moniker"] = status_validator_data["result"]["node_info"]["moniker"]
                            validators[address]["chain_id"] = status_validator_data["result"]["node_info"]["network"]
                    except requests.RequestException as e:
                        print(f"Error connecting to {peer['remote_ip']}: {e}")
        except Exception as e:
            print(f"Error fetching validator data: {e}")
        
        # Sort by Moniker a-z
        validators = dict(sorted(validators.items(), key=lambda item: item[1]["moniker"]))
        return validators

    async def update_table(self, seed_node):
        while True:
            self.validator_list = self.get_validators(seed_node)
            self.table = urwid.Pile([
                urwid.Columns([urwid.Text("IP"), urwid.Text("Latest Block Height"), urwid.Text("Syncing"), urwid.Text("Moniker"), urwid.Text("Chain ID")], dividechars=2)
            ] + [
                urwid.Columns([
                    urwid.Text(validator["ip"]),
                    urwid.Text(validator["latest_block_height"]),
                    urwid.Text(str(validator["catching_up"])),
                    urwid.Text(validator["moniker"]),
                    urwid.Text(validator["chain_id"])
                ], dividechars=2) for address, validator in self.validator_list.items()
            ])
            self.menu.contents[0] = (urwid.Filler(self.table, valign="top"), self.menu.options())
            await asyncio.sleep(5)

    def __init__(self):
        self.menu = urwid.Pile([(urwid.Text("Loading..."))])
        self.loop = urwid.AsyncioEventLoop(loop=asyncio.get_event_loop())
        self.main_loop = urwid.MainLoop(self.menu, event_loop=self.loop, unhandled_input=self.exit_on_q)

    def exit_on_q(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

    def run(self, seed_node):
        asyncio.ensure_future(self.update_table(seed_node))
        self.main_loop.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validator Debugger")
    parser.add_argument("--seed-node", help="Seed node IP address", default="116.203.81.165")
    args = parser.parse_args()
    validator_debugger = ValidatorDebugger()
    validator_debugger.run(args.seed_node)