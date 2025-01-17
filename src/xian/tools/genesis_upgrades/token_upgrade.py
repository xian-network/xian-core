import ast
from ast import NodeTransformer, AST
import json
from typing import List, Tuple

class TokenFunctionTransformer(NodeTransformer):
    """AST transformer for updating XSC001 token functions"""
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit and potentially transform function definitions"""
        # First apply any base class transformations
        node = self.generic_visit(node)
        
        if node.name == 'approve':
            new_body = self._update_approve_function(node)
            # Preserve original decorator
            new_body.decorator_list = node.decorator_list
            return new_body
        elif node.name == 'transfer_from':
            new_body = self._update_transfer_from_function(node)
            # Preserve original decorator
            new_body.decorator_list = node.decorator_list
            return new_body
        
        return node

    def _update_approve_function(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Update the approve function with new checks"""
        new_body = ast.parse("""
def approve(amount: float, to: str):
    assert amount > 0, 'Cannot approve negative balances!'
    __approvals[ctx.caller, to] = amount
    return f'Approved {amount} for {to}'
""").body[0]
        
        # Preserve original decorator
        new_body.decorator_list = node.decorator_list
        return new_body

    def _update_transfer_from_function(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Update the transfer_from function with new checks"""
        new_body = ast.parse("""
def transfer_from(amount: float, to: str, main_account: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert __approvals[main_account, ctx.caller] >= amount, 'Not enough coins approved to send!'
    assert __balances[main_account] >= amount, 'Not enough coins to send!'
    
    __approvals[main_account, ctx.caller] -= amount
    __balances[main_account] -= amount
    __balances[to] += amount
    return f'Sent {amount} to {to} from {main_account}'
""").body[0]
        
        # Preserve original decorator
        new_body.decorator_list = node.decorator_list
        return new_body

    def visit_Module(self, node: ast.Module) -> ast.Module:
        """Add new imports and state variables at the module level"""
        # First apply any base class transformations
        node = self.generic_visit(node)
        
        # Add new imports and state variables at the top
        new_header = ast.parse("""
__approvals = Hash(default_value=0)
""").body

        
        # Combine everything
        node.body = new_header + node.body
        return node

def find_code_entries(genesis_data: dict) -> List[Tuple[int, str, str]]:
    """
    Find all entries in genesis data that contain .__code__ and return their indices and values
    Returns: List of tuples containing (index, contract_name, code_value)
    """
    code_entries = []
    
    for idx, entry in enumerate(genesis_data['abci_genesis']['genesis']):
        key = entry.get('key', '')
        if key.endswith('.__code__') and key.startswith('con_') and "pixel" not in key:
            contract_name = key.replace('.__code__', '')
            code_entries.append((idx, contract_name, entry['value']))
    
    return code_entries

def is_xsc001_token(code: str) -> bool:
    """
    Check if the given code matches XSC001 token structure
    """
    # Basic checks for XSC001 token structure
    required_elements = [
        '__balances = Hash(',
        '__metadata = Hash(',
        'def transfer(',
        'def approve(',
        'def transfer_from('
    ]
    
    return all(element in code for element in required_elements)

def is_xsc002_token(code: str) -> bool:
    """
    Check if the given code matches XSC002 token structure
    """
    required_elements = [
        '__balances = Hash(',
        '__metadata = Hash(',
        '__permits = Hash(',
        '__streams = Hash(',
        'def transfer(',
        'def approve(',
        'def transfer_from(',
        'def permit('
    ]
    return all(element in code for element in required_elements)

def process_genesis_data(genesis_data: dict):
    """
    Main function to process the genesis data
    Args:
        genesis_data: Dictionary containing the genesis data
    """
    # Find all code entries
    code_entries = find_code_entries(genesis_data)
    
    # Track if any changes were made
    changes_made = False
    
    # Process each code entry
    for idx, contract_name, code_value in code_entries:
        # Check if it's an XSC001 token
        if is_xsc001_token(code_value):
            print(f"Found XSC001 token contract: {contract_name} at index {idx}")
            
            # Here you would:
            # 1. Reverse process the code (using your existing function)
            # processed_code = your_reverse_processing_function(code_value)
            
            # 2. Add new line at beginning and update functions
            updated_code = update_xsc001_token_code(code_value)
            
            # 3. Process the updated code back to genesis format
            # final_code = your_processing_function(updated_code)
            
            # 4. Update the genesis data
            genesis_data['abci_genesis']['genesis'][idx]['value'] = updated_code
            changes_made = True

    return genesis_data, changes_made

def update_xsc001_token_code(code: str) -> str:
    """
    Update the token code with new functionality using AST transformation
    """
    # Parse the code into an AST
    tree = ast.parse(code)
    
    # Apply our transformations
    transformer = TokenFunctionTransformer()
    modified_tree = transformer.visit(tree)
    
    # Convert back to source code
    return ast.unparse(modified_tree)

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
        print("No XSC001 tokens found, no changes made")
