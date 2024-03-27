import importlib
import sys
import logging
import os
import gc


class UpgradeHandler():
    """
    This class enables seamless blockchain upgrades, avoiding hard forks by allowing dynamic switching between method versions at specific block heights. 
    It ensures synchronization and transaction replay with consistent hash results across blockchain versions. 
    The class uses versioned files, switching from version x to version y at predetermined block heights to maintain data integrity and compatibility.
    It leverages the importlib library for dynamic loading and unloading of modules (ex. finalize_block_v1.py, finalize_block_v2.py, etc.), 
    facilitating live updates to logic without network downtime or manual module replacement.
    """
    def __init__(self, app):
        self.current_version = "v1"
        self.app = app

    def change_version(self, version: str):
        """
        This function changes the working version of modules by dynamically loading
        modules based on the specified version. For version 'v1', it looks for files without
        the '_v' marker. For versions beyond 'v1', it looks for files with the corresponding
        version marker (e.g., '_v2.py').
        """
        try:
            project_dir = os.path.dirname(os.path.realpath(__file__))
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    # For version 'v1', load files without '_v' in their name
                    if version == "v1" and '_v' not in file and file.endswith(".py"):
                        self._load_module(file, root, project_dir)
                    # For other versions, check for the appropriate version marker in the file name
                    elif f"_{version}.py" in file:
                        self._load_module(file, root, project_dir)
            logging.info(f"Changed to version {version}")
        except Exception as e:
            raise Exception(f"Upgrade failed: {e}")

    def _load_module(self, file, root, project_dir):
        """
        Helper function to load or reload a module given its filename and directory.
        """
        relative_path = os.path.relpath(os.path.join(root, file), start=project_dir)
        module_path = relative_path.replace(os.path.sep, '.')[:-3]  # remove '.py' extension
        original_module_path = module_path.replace(f"_v{self.current_version}", "") if self.current_version != "v1" else module_path.split('_v')[0]

        # Prepend xian.
        module_path = f"xian.{module_path}"
        original_module_path = f"xian.{original_module_path}"

        self.app._load_module(module_path, original_module_path)

        # Explicitly collect garbage
        gc.collect()

           
    def check_version(self, block_height: int):
        """
        Check if a version change is required based on the current block height.
        """
        if block_height >= 1 and self.current_version == "v1":
            self.change_version("v2")
            self.current_version = "v2"
        # if block_height >= 200000 and block_height < 300000 and self.current_version == "v2":
        #     self.change_version("v3")
        #     self.current_version = "v3"

        # Btw. there is no issue with downgrading either

        # if block_height >= 300000 and self.current_version == "v3":
        #     self.change_version("v2")
        #     self.current_version = "v2"
