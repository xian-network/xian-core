import json
import os
import binascii
import marshal
from loguru import logger
from xian.utils.encoding import hash_bytes
from contracting.storage.encoder import convert_dict
from contracting.compilation.compiler import ContractingCompiler

def compile_contract_from_source(s: dict):
    """Transform and compile contract code, returning both transformed source and bytecode."""

    contract_name = s["key"].split(".")[0]
    compiler = ContractingCompiler(module_name=contract_name)
    
    transformed_code = compiler.parse_to_code(s["value"])
    
    compiled_code = compiler.compile(s["value"])
    serialized_code = marshal.dumps(compiled_code)
    hexadecimal_string = binascii.hexlify(serialized_code).decode()
    
    logger.info(f"Transformed and compiled contract code for {contract_name}")
    return transformed_code, hexadecimal_string

def hash_from_state_changes(state_changes):
    """Generate a hash from a list of state changes."""
    # Convert state changes to a serializable format
    serialized_changes = []
    for change in state_changes:
        serialized_change = {
            "key": change["key"],
            "value": json.dumps(change["value"], sort_keys=True)
            # Note: We exclude comments from the hash as they don't affect state
        }
        serialized_changes.append(serialized_change)
    
    serialized_changes.sort(key=lambda x: x["key"])
    
    changes_str = json.dumps(serialized_changes, sort_keys=True)
    
    hash_obj = hash_bytes(changes_str.encode())
    if isinstance(hash_obj, bytes):
        return hash_obj.hex()
    return hash_obj

class StatePatchManager:
    def __init__(self, raw_driver):
        self.patches = {}
        self.raw_driver = raw_driver
        self.loaded = False
    
    def load_patches(self, patch_file_path):
        """Load all state patches from the specified JSON file."""
        if not os.path.exists(patch_file_path):
            logger.info(f"No state patches file found at {patch_file_path}")
            self.loaded = True
            return
        
        try:
            with open(patch_file_path, 'r') as f:
                patch_data = json.load(f)
            
            # Convert string keys (block heights) to integers for easier comparison
            self.patches = {int(height): patches for height, patches in patch_data.items()}
            logger.info(f"Loaded patches for {len(self.patches)} blocks")
            self.loaded = True
        except Exception as e:
            logger.error(f"Error loading state patches: {e}")
            # Initialize empty to avoid errors
            self.patches = {}
            self.loaded = False
    
    def apply_patches_for_block(self, height, nanos) -> tuple[str | None, list]:
        """Apply any patches for the specified block height and return hash and applied patches."""
        if not self.loaded or height not in self.patches:
            return None, []
        
        patches = self.patches[height]
        if not patches:
            return None, []
            
        logger.info(f"Applying {len(patches)} state patches for block {height}")
        
        applied_patches = []
        
        for patch in patches:
            key = patch["key"]
            value = patch["value"]
            comment = patch.get("comment", "No comment provided")
            
            logger.info(f"Applying patch: {key} -> {value} ({comment})")
            
            # Track the patch being applied (deep copy to avoid modification)
            applied_patch = {
                "key": key,
                "value": value,
                "comment": comment
            }
            applied_patches.append(applied_patch)
            
            # Check if this is a contract code patch
            # Contract code key format: con_contract_name.__code__
            parts = key.split(".")
            if len(parts) > 1 and parts[1] == "__code__":
                contract_name = parts[0]
                
                logger.info(f'Processing contract code patch: {contract_name}')
                
                try:
                    transformed_code, compiled_code = compile_contract_from_source(patch)
                    
                    self.raw_driver.set(key, transformed_code)
                    self.raw_driver.set(f"{contract_name}.__compiled__", compiled_code)
                    
                    # For BDS, we want to record both the original code and the compiled code
                    # First add the original code to applied patches
                    original_code_patch = {
                        "key": key,
                        "value": patch["value"],  # Original code
                        "comment": f"Original source code for {comment}"
                    }
                    applied_patches.append(original_code_patch)
                    
                    # Then add the compiled code
                    compiled_patch = {
                        "key": f"{contract_name}.__compiled__",
                        "value": compiled_code,
                        "comment": f"Compiled bytecode for {comment}"
                    }
                    applied_patches.append(compiled_patch)
                    
                    logger.info(f'Contract code patch applied for {contract_name}')
                except Exception as e:
                    # Log the error but continue processing other patches
                    logger.error(f'Failed to compile contract code for {contract_name}: {e}')
                    logger.error(f'Skipping this patch and continuing with others')
                    
                    # Remove this patch from applied_patches since it wasn't actually applied
                    applied_patches.pop()
            else:
                # Handle all other (non-code) patches
                # Convert dict values if needed
                if isinstance(value, dict):
                    value = convert_dict(value)
                
                # Apply the patch to state
                self.raw_driver.set(key, value)
        
        # Finalize changes
        self.raw_driver.hard_apply(nanos)
        
        # Generate a hash of the state patches
        patch_hash = hash_from_state_changes(patches)
        logger.info(f"Generated hash for state patches: {patch_hash}")
        
        return patch_hash, applied_patches 