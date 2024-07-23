import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import shutil
from utils import setup_cometbft_tmp, teardown_cometbft_tmp

class TestSetupCometbftTmp(unittest.TestCase):

    @patch('shutil.copytree')
    @patch('shutil.rmtree')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.mkdir')
    def test_setup_cometbft_tmp(self, mock_mkdir, mock_is_dir, mock_exists, mock_rmtree, mock_copytree):
        # Mock the Path.exists() and Path.is_dir() methods
        mock_exists.return_value = True
        mock_is_dir.return_value = True

        # Call the function
        setup_cometbft_tmp()

        # Check if teardown_cometbft_tmp was called
        mock_rmtree.assert_called_once_with(Path('/tmp/cometbft/'))

        # Check if the directory was copied
        mock_copytree.assert_called_once_with(Path('fixtures/.cometbft-fixture'), Path('/tmp/cometbft/'))

    @patch('shutil.rmtree')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_teardown_cometbft_tmp(self, mock_is_dir, mock_exists, mock_rmtree):
        # Mock the Path.exists() and Path.is_dir() methods
        mock_exists.return_value = True
        mock_is_dir.return_value = True

        # Call the function
        teardown_cometbft_tmp()

        # Check if the directory was removed
        mock_rmtree.assert_called_once_with(Path('/tmp/cometbft/'))        

if __name__ == '__main__':
    unittest.main()