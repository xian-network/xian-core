import ast
from ast import NodeTransformer
import json
from typing import List, Tuple

class TokenFunctionTransformer(NodeTransformer):
    """AST transformer for updating XSC001 token functions"""
    def __init__(self, contract_name: str):
        self.contract_name = contract_name
        
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit and potentially transform function definitions"""
        # First apply any base class transformations
        node = self.generic_visit(node)
        
        if node.name == 'approve':
            new_body = self._update_approve_function(node)
            new_body.decorator_list = node.decorator_list
            return new_body
        elif node.name == 'transfer_from':
            new_body = self._update_transfer_from_function(node)
            new_body.decorator_list = node.decorator_list
            return new_body
        elif node.name == 'permit':
            new_body = self._update_permit_function(node)
            new_body.decorator_list = node.decorator_list
            return new_body
        elif node.name == 'balance_of':
            new_body = self._update_balance_of_function(node)
            new_body.decorator_list = node.decorator_list
            return new_body
        elif node.name == '__construct_permit_msg':
            new_body = self._update_construct_permit_msg_function(node)
            new_body.decorator_list = node.decorator_list
            return new_body
        return node

    def _update_approve_function(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Update the approve function with new checks"""
        new_body = ast.parse("""
def approve(amount: float, to: str):
    assert amount >= 0, "Cannot approve negative balances."
    __balances[ctx.caller, to] = amount

    __ApproveEvent({"from": ctx.caller, "to": to, "amount": amount})

""").body[0]
        
        # Preserve original decorator
        new_body.decorator_list = node.decorator_list
        return new_body
    
    
    def _update_transfer_from_function(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Update the transfer_from function"""
        new_body = ast.parse("""
def transfer_from(amount: float, to: str, main_account: str):
    assert amount > 0, 'Cannot send negative balances!'
    assert __balances[main_account, ctx.caller] >= amount, f'Not enough coins approved to send! You have {__balances[main_account, ctx.caller]} and are trying to spend {amount}'
    assert __balances[main_account] >= amount, 'Not enough coins to send!'

    __balances[main_account, ctx.caller] -= amount
    __balances[main_account] -= amount
    __balances[to] += amount

    __TransferEvent({"from": main_account, "to": to, "amount": amount})
""").body[0]
        
        # Preserve original decorator
        new_body.decorator_list = node.decorator_list
        return new_body

        
    def _update_permit_function(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Update the permit function"""
        new_body = ast.parse("""
def permit(owner: str, spender: str, value: float, deadline: str, signature: str):
    deadline = __strptime_ymdhms(deadline)
    permit_msg = __construct_permit_msg(owner, spender, value, str(deadline))
    permit_hash = hashlib.sha3(permit_msg)

    assert __permits[permit_hash] is None, 'Permit can only be used once.'
    assert value >= 0, 'Cannot approve negative balances!'
    assert now < deadline, 'Permit has expired.'
    assert crypto.verify(owner, permit_msg, signature), 'Invalid signature.'

    __balances[owner, spender] = value
    __permits[permit_hash] = True

    __ApproveEvent({"from": owner, "to": spender, "amount": value})
    
    return permit_hash
""").body[0]
        
        # Preserve original decorator
        new_body.decorator_list = node.decorator_list
        return new_body
    
    def _update_balance_of_function(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Update the balance_of function"""
        new_body = ast.parse("""
def balance_of(address: str):
    return __balances[address]
""").body[0]
        
        # Preserve original decorator
        new_body.decorator_list = node.decorator_list
        return new_body
    
    def _update_construct_permit_msg_function(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Update the construct_permit_msg function"""
        new_body = ast.parse("""
def __construct_permit_msg(owner: str, spender: str, value: float, deadline: str):
    return f"{owner}:{spender}:{value}:{deadline}:{ctx.this}:{chain_id}"
""").body[0]
        
        # Preserve original decorator
        new_body.decorator_list = node.decorator_list
        return new_body

    def visit_Module(self, node: ast.Module) -> ast.Module:
        """Add new imports and state variables at the module level"""
        # First check if balance_of already exists
        has_balance_of = any(
            isinstance(n, ast.FunctionDef) and n.name == 'balance_of'
            for n in node.body
        )
        
        # Apply existing transformations
        node = self.generic_visit(node)
        
        # Adds events to top of contract if they are missing...
        if needs_xsc001_events(node.body):
            new_header = xsc001_header(self.contract_name)
        
        # Add balance_of function if it doesn't exist
        if not has_balance_of:
            balance_of_func = ast.parse(f"""
@__export('{self.contract_name}')
def balance_of(address: str):
    return __balances[address]
""").body
            node.body = new_header + node.body + balance_of_func
        else:
            node.body = new_header + node.body
            
        return node

def find_code_entries(genesis_data: dict) -> List[Tuple[int, str, str]]:
    """
    Find all entries in genesis data that contain .__code__ and return their indices and values
    Returns: List of tuples containing (index, contract_name, code_value)
    """
    code_entries = []
    
    excluded_contracts = [
        "con_snake.__code__",
        "con_xfinxty.__code__",
        "con_stk.__code__",
        "con_stk001.__code__",
        "con_stk5.__code__",
        "con_stk6.__code__",
        "con_stk003.__code__",
        "con_stk005.__code__",
        "con_stk006.__code__",
        "con_snake.__code__",
    ]
    
    for idx, entry in enumerate(genesis_data['abci_genesis']['genesis']):
        key = entry.get('key', '')
        if (
            key.endswith('.__code__') and 
            key.startswith('con_') and 
            "pixel" not in key and 
            key not in excluded_contracts
        ):
            contract_name = key.replace('.__code__', '')
            code_entries.append((idx, contract_name, entry['value']))
    
    return code_entries

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
        if is_xsc001_token(code_value):
            print(f"Found XSC001 token contract: {contract_name} at index {idx}")
            updated_code = update_token_code(contract_name, code_value)
            genesis_data['abci_genesis']['genesis'][idx]['value'] = updated_code
            changes_made = True

    return genesis_data, changes_made

def update_token_code(contract_name: str, code: str) -> str:
    """
    Update the token code with new functionality using AST transformation
    """
    # Parse the code into an AST
    tree = ast.parse(code)
    
    # Apply our transformations
    transformer = TokenFunctionTransformer(contract_name)
    modified_tree = transformer.visit(tree)
    
    # Convert back to source code
    return ast.unparse(modified_tree)


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
    
    # Note: We don't include balance_of in required_elements since we'll add it if missing
    return all(element in code for element in required_elements)

    
def needs_xsc001_events(code: str) -> bool:
    xsc001_events = [
        'TransferEvent = LogEvent(',
        'ApproveEvent = LogEvent(',
    ]
    return not any(element in code for element in xsc001_events)

    
def xsc001_header(contract_name: str):
    return ast.parse(f'''
__TransferEvent = LogEvent(event="Transfer", params={{"from": {{"type": str, "idx": True}}, "to": {{"type": str, "idx": True}}, "amount": {{"type": (int, float, decimal)}}}}, contract="{contract_name}", name="TransferEvent")
__ApproveEvent = LogEvent(event="Approve", params={{"from": {{"type": str, "idx": True}}, "to": {{"type": str, "idx": True}}, "amount": {{"type": (int, float, decimal)}}}}, contract="{contract_name}", name="ApproveEvent")
''').body


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
