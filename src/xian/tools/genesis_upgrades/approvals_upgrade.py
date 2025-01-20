import json
from typing import List, Dict, Tuple

def find_xsc001_tokens(genesis_data: dict) -> List[str]:
    """Find all XSC001 token contracts in genesis data"""
    token_contracts = []
    
    for entry in genesis_data['abci_genesis']['genesis']:
        key = entry.get('key', '')
        if key.endswith('.__code__') and "pixel" not in key:
            contract_name = key.replace('.__code__', '')
            code = entry['value']
            
            # Check if it's an XSC001 token
            required_elements = [
                '__balances = Hash(',
                '__metadata = Hash(',
                'def transfer(',
                'def approve(',
                'def transfer_from('
            ]
            
            if all(element in code for element in required_elements):
                token_contracts.append(contract_name)
    
    return token_contracts

def migrate_approvals(genesis_data: dict, token_contracts: List[str]) -> Tuple[dict, bool]:
    """
    Migrate old approval format to new format for specified token contracts
    Returns: (updated_genesis_data, changes_made)
    """
    changes_made = False
    new_genesis = []
    
    for entry in genesis_data['abci_genesis']['genesis']:
        key = entry.get('key', '')
        
        # Check if this is an approval entry that needs migration
        is_approval = False
        for contract in token_contracts:
            if key.startswith(f"{contract}.balances:") and ":" in key[len(contract)+10:]:
                # This is an approval entry that needs to be migrated
                # Original format: contract.balances:sender:spender
                # New format: contract.approvals:sender:spender
                new_key = key.replace(f"{contract}.balances:", f"{contract}.approvals:")
                new_entry = {
                    'key': new_key,
                    'value': entry['value']
                }
                new_genesis.append(new_entry)
                changes_made = True
                is_approval = True
                break
        
        # If it's not an approval entry, keep it
        if not is_approval:
            new_genesis.append(entry)
    
    genesis_data['abci_genesis']['genesis'] = new_genesis
    return genesis_data, changes_made

def process_genesis_data(genesis_data: dict) -> Tuple[dict, bool]:
    """
    Main function to process the genesis data
    Returns: (updated_genesis_data, changes_made)
    """
    # First find all XSC001 tokens
    token_contracts = find_xsc001_tokens(genesis_data)
    
    if not token_contracts:
        print("No XSC001 tokens found")
        return genesis_data, False
    
    print(f"Found {len(token_contracts)} XSC001 tokens:")
    for contract in token_contracts:
        print(f"  - {contract}")
    
    # Then migrate approvals for these tokens
    return migrate_approvals(genesis_data, token_contracts)

if __name__ == "__main__":
    genesis_file_path = "./genesis.json"
    
    # Read the genesis file
    with open(genesis_file_path, 'r') as f:
        genesis_data = json.load(f)
    
    # Process the genesis data
    updated_genesis, changes_made = process_genesis_data(genesis_data)
    
    if changes_made:
        # Generate output filename based on input
        import os
        dir_path = os.path.dirname(genesis_file_path)
        base_name = os.path.basename(genesis_file_path)
        name, ext = os.path.splitext(base_name)
        output_path = os.path.join(dir_path, f"{name}_updated{ext}")
        
        # Write the updated genesis file
        with open(output_path, 'w') as f:
            json.dump(updated_genesis, f, indent=4)
        print(f"Updated genesis file written to: {output_path}")
    else:
        print("No changes were made to the genesis file")
