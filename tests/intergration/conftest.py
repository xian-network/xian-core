import pytest
import os
from pathlib import Path
import shutil

@pytest.fixture(scope="function", autouse=True)
def setup_fixtures():
    # Set the working directory to the directory containing this file
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Ensure the fixtures directory exists
    fixtures_dir = Path("fixtures/.cometbft-fixture")
    if not fixtures_dir.exists():
        raise FileNotFoundError(f"Fixture directory {fixtures_dir} does not exist.")
    
    # Ensure the temporary directory is set up
    cometbft_tmp_dir = Path("/tmp/cometbft/")
    if cometbft_tmp_dir.exists():
        shutil.rmtree(cometbft_tmp_dir)
    shutil.copytree(fixtures_dir, cometbft_tmp_dir)
    
    yield
    
    # Cleanup after tests
    if cometbft_tmp_dir.exists():
        shutil.rmtree(cometbft_tmp_dir)