"""
Pytest configuration and fixtures for doti tests

This module provides common fixtures and test configuration for all doti tests.
"""

import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import Mock

from doti import Doti


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_doti_dir(temp_dir):
    """Create a mock doti directory structure"""
    doti_dir = temp_dir / ".doti"
    doti_dir.mkdir()
    (doti_dir / "storage").mkdir()
    (doti_dir / "hooks").mkdir()
    (doti_dir / "config.json").write_text("{}")
    return doti_dir


@pytest.fixture
def test_file(temp_dir):
    """Create a test file for testing"""
    test_file = temp_dir / "test_config.txt"
    test_file.write_text("Test configuration content")
    return test_file


@pytest.fixture
def sensitive_file(temp_dir):
    """Create a sensitive test file"""
    sensitive_file = temp_dir / ".ssh" / "config"
    sensitive_file.parent.mkdir()
    sensitive_file.write_text("Host *\n    StrictHostKeyChecking no")
    # Set restrictive permissions
    sensitive_file.chmod(0o600)
    return sensitive_file


@pytest.fixture
def doti_instance(mock_doti_dir):
    """Create a Doti instance with mocked directory"""
    # Mock the home directory to use our temp directory
    original_home = Path.home()
    mock_home = mock_doti_dir.parent
    
    # Temporarily override home directory
    import doti.core
    original_init = doti.core.Doti.__init__
    
    def mock_init(self):
        self.doti_dir = mock_home / ".doti"
        self.storage_dir = self.doti_dir / "storage"
        self.hooks_dir = self.doti_dir / "hooks"
        self.config_file = self.doti_dir / "config.json"
        self.audit_file = self.doti_dir / "audit.log"
        self._config_cache = None
        self._config_dirty = False
    
    doti.core.Doti.__init__ = mock_init
    
    yield Doti()
    
    # Restore original __init__
    doti.core.Doti.__init__ = original_init


@pytest.fixture
def sample_config():
    """Sample configuration data"""
    return {
        "/home/user/.bashrc": {
            "storage_path": "/home/user/.doti/storage/bashrc",
            "original_name": "bashrc"
        },
        "/home/user/.vimrc": {
            "storage_path": "/home/user/.doti/storage/vimrc",
            "original_name": "vimrc"
        }
    }
