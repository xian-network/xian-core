from pathlib import Path
import shutil
import os
    
def setup_cometbft_tmp():
    # Copy the contents of the fixture folder to the temporary directory.
    # ensure that the temporary directory, /tmp/cometbft/ is empty before copying.
    teardown_cometbft_tmp()
    copy_fixture_to_cometbft_tmp()
    
def copy_fixture_to_cometbft_tmp():
    # Copy the contents of the fixture folder to the temporary directory.
    # ensure that the temporary directory, /tmp/cometbft/ is empty before copying.
    fixture_ = Path('./fixtures/.cometbft-fixture')
    cometbft_tmp_ = Path('/tmp/cometbft/')
    shutil.copytree(fixture_, cometbft_tmp_)

def teardown_cometbft_tmp():
    # Remove the temporary directory /tmp/cometbft/ and all its contents.
    cometbft_tmp_ = Path('/tmp/cometbft/')
    if cometbft_tmp_.exists() and cometbft_tmp_.is_dir():
        shutil.rmtree(cometbft_tmp_)

def setup_fixtures():
    # Set the working directory to the directory containing this file
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Ensure the fixtures directory exists
    fixtures_dir = Path("./fixtures/.cometbft-fixture")
    if not fixtures_dir.exists():
        raise FileNotFoundError(f"Fixture directory {fixtures_dir} does not exist.")
    
    # Ensure the temporary directory is set up
    cometbft_tmp_dir = Path("/tmp/cometbft/")
    if cometbft_tmp_dir.exists():
        shutil.rmtree(cometbft_tmp_dir)
    shutil.copytree(fixtures_dir, cometbft_tmp_dir)
    
    
    # Cleanup after tests

def teardown_fixtures():
    cometbft_tmp_dir = Path("/tmp/cometbft/")
    if cometbft_tmp_dir.exists():
        shutil.rmtree(cometbft_tmp_dir)