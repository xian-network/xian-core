from pathlib import Path
import shutil
    
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
