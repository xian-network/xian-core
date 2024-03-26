import importlib
import sys
import logging
import os


class UpgradeHandler():
    """
    This class enables seamless blockchain upgrades, avoiding hard forks by allowing dynamic switching between method versions at specific block heights. 
    It ensures synchronization and transaction replay with consistent hash results across blockchain versions. 
    The class uses versioned files, switching from version x to version y at predetermined block heights to maintain data integrity and compatibility.
    It leverages the importlib library for dynamic loading and unloading of modules (ex. finalize_block_v1.py, finalize_block_v2.py, etc.), 
    facilitating live updates to logic without network downtime or manual module replacement.
    """
    def __init__(self):
        self.current_version = "v1"

    def upgrade(self, version: str):
        """
        Recursively crawls the project folder for files ending with the specified version number
        and dynamically loads the new module.
        """
        try:
            project_dir = os.path.dirname(os.path.realpath(__file__))
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    if file.endswith(f"_{version}.py"):
                        # Construct module name based on file path relative to project_dir
                        # and convert it to a Python module path.
                        relative_path = os.path.relpath(os.path.join(root, file), start=project_dir)
                        module_path = relative_path.replace(os.path.sep, '.')[:-3]  # remove '.py' extension
                        original_module_name = file.split("_v")[0]
                        # Changing the current module to the new one
                        sys.modules[original_module_name] = importlib.import_module(module_path)
                        # Reloading the module
                        importlib.reload(sys.modules[original_module_name])
                        logging.info(f"Upgraded to version {version}")
        except Exception as e:
            raise Exception(f"Upgrade failed: {e}")
           
    def check_upgrade(self, block_height: int):
        """
        Check if an upgrade is needed at the given block height.
        """
        # if block_height >= 100000 and block_height < 200000 and self.current_version == "v1":
        #     self.upgrade("v2")
        #     self.current_version = "v2"
        # if block_height >= 200000 and self.current_version == "v2":
        #     self.upgrade("v3")
        #     self.current_version = "v3"