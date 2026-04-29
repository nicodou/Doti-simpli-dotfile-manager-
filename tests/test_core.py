"""
Unit tests for doti core functionality

This module tests the core Doti class methods and functionality.
"""

import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

from doti.core import Doti


class TestDotiBasicFunctionality:
    """Test basic Doti functionality without new features"""
    
    def test_doti_initialization(self, mock_doti_dir):
        """Test Doti instance initialization"""
        doti = Doti()
        assert doti.doti_dir.exists()
        assert doti.storage_dir.exists()
        assert doti.hooks_dir.exists()
        assert doti.config_file.exists()
    
    def test_init_creates_directories(self, temp_dir):
        """Test init creates necessary directories"""
        # Mock home directory
        with patch('pathlib.Path.home', return_value=temp_dir):
            doti = Doti()
            success = doti.init()
            
            assert success is True
            assert doti.doti_dir.exists()
            assert doti.storage_dir.exists()
            assert doti.hooks_dir.exists()
            assert doti.config_file.exists()
            
            # Check config file content
            config = json.loads(doti.config_file.read_text())
            assert config == {}
    
    def test_init_dry_run(self, temp_dir):
        """Test init in dry-run mode"""
        with patch('pathlib.Path.home', return_value=temp_dir):
            doti = Doti()
            success = doti.init(dry_run=True)
            
            assert success is True
            # Directories should not be created in dry run
            assert not doti.doti_dir.exists()
    
    def test_load_config(self, doti_instance, sample_config):
        """Test loading configuration"""
        # Setup sample config
        doti_instance.config_file.write_text(json.dumps(sample_config, indent=2))
        
        config = doti_instance._load_config()
        assert config == sample_config
    
    def test_load_config_cache(self, doti_instance, sample_config):
        """Test configuration caching"""
        doti_instance.config_file.write_text(json.dumps(sample_config, indent=2))
        
        # First load
        config1 = doti_instance._load_config()
        # Second load (should use cache)
        config2 = doti_instance._load_config()
        
        assert config1 is config2  # Should be same object (cached)
    
    def test_save_config(self, doti_instance, sample_config):
        """Test saving configuration"""
        doti_instance._save_config(sample_config)
        
        loaded_config = json.loads(doti_instance.config_file.read_text())
        assert loaded_config == sample_config
    
    def test_ensure_directories(self, doti_instance):
        """Test ensuring directories exist"""
        # Remove doti directory
        shutil.rmtree(doti_instance.doti_dir)
        
        # Should recreate directories
        result = doti_instance._ensure_directories()
        assert result is True
        assert doti_instance.doti_dir.exists()


class TestDotiAddFile:
    """Test add_file functionality"""
    
    def test_add_file_basic(self, doti_instance, test_file):
        """Test basic file addition"""
        success = doti_instance.add_file(str(test_file))
        
        assert success is True
        assert test_file.is_symlink()
        
        # Check config
        config = doti_instance._load_config()
        assert str(test_file) in config
        
        data = config[str(test_file)]
        assert data["original_name"] == test_file.name
        assert Path(data["storage_path"]).exists()
    
    def test_add_file_nonexistent(self, doti_instance, temp_dir):
        """Test adding non-existent file"""
        nonexistent = temp_dir / "nonexistent.txt"
        
        success = doti_instance.add_file(str(nonexistent))
        assert success is False
    
    def test_add_file_already_managed(self, doti_instance, test_file):
        """Test adding already managed file"""
        # Add file first time
        doti_instance.add_file(str(test_file))
        
        # Try to add again
        success = doti_instance.add_file(str(test_file))
        assert success is False
    
    def test_add_file_dry_run(self, doti_instance, test_file):
        """Test add_file in dry-run mode"""
        success = doti_instance.add_file(str(test_file), dry_run=True)
        
        assert success is True
        assert not test_file.is_symlink()  # Should not create symlink
        assert not list(doti_instance.storage_dir.glob("*"))  # No files in storage
    
    def test_get_unique_storage_path(self, doti_instance, temp_dir):
        """Test getting unique storage path for conflicts"""
        # Create existing file in storage
        existing_file = doti_instance.storage_dir / "test.txt"
        existing_file.write_text("existing")
        
        test_file = temp_dir / "test.txt"
        test_file.write_text("new content")
        
        unique_path = doti_instance._get_unique_storage_path(test_file)
        
        assert unique_path.name != "test.txt"  # Should be different
        assert unique_path.parent == doti_instance.storage_dir
        assert not unique_path.exists()


class TestDotiDeploy:
    """Test deploy functionality"""
    
    def test_deploy_basic(self, doti_instance, test_file):
        """Test basic deploy functionality"""
        # Add a file first
        doti_instance.add_file(str(test_file))
        
        # Remove symlink to test deploy
        test_file.unlink()
        
        success = doti_instance.deploy()
        assert success is True
        assert test_file.is_symlink()
    
    def test_deploy_no_files(self, doti_instance):
        """Test deploy with no managed files"""
        success = doti_instance.deploy()
        assert success is True
    
    def test_deploy_dry_run(self, doti_instance, test_file):
        """Test deploy in dry-run mode"""
        doti_instance.add_file(str(test_file))
        test_file.unlink()
        
        success = doti_instance.deploy(dry_run=True)
        assert success is True
        assert not test_file.is_symlink()  # Should not create symlink


class TestDotiUnlink:
    """Test unlink functionality"""
    
    def test_unlink_basic(self, doti_instance, test_file):
        """Test basic unlink functionality"""
        # Add file first
        doti_instance.add_file(str(test_file))
        
        success = doti_instance.unlink(str(test_file))
        
        assert success is True
        assert not test_file.is_symlink()
        assert test_file.exists()  # File should be restored
        
        # Check config
        config = doti_instance._load_config()
        assert str(test_file) not in config
    
    def test_unlink_no_restore(self, doti_instance, test_file):
        """Test unlink without restoring file"""
        doti_instance.add_file(str(test_file))
        
        success = doti_instance.unlink(str(test_file), restore=False)
        
        assert success is True
        assert not test_file.is_symlink()
        assert not test_file.exists()  # File should not be restored
    
    def test_unlink_non_managed(self, doti_instance, test_file):
        """Test unlink non-managed file"""
        success = doti_instance.unlink(str(test_file))
        assert success is False
    
    def test_unlink_dry_run(self, doti_instance, test_file):
        """Test unlink in dry-run mode"""
        doti_instance.add_file(str(test_file))
        
        success = doti_instance.unlink(str(test_file), dry_run=True)
        
        assert success is True
        assert test_file.is_symlink()  # Should not unlink in dry run


class TestDotiList:
    """Test list functionality"""
    
    def test_list_no_files(self, doti_instance, capsys):
        """Test list with no managed files"""
        doti_instance.list()
        captured = capsys.readouterr()
        assert "No managed files" in captured.out
    
    def test_list_with_files(self, doti_instance, test_file):
        """Test list with managed files"""
        doti_instance.add_file(str(test_file))
        
        with patch('builtins.print') as mock_print:
            doti_instance.list()
            # Should print file information
            assert mock_print.called


class TestDotiDoctor:
    """Test doctor functionality"""
    
    def test_doctor_no_files(self, doti_instance):
        """Test doctor with no managed files"""
        success = doti_instance.doctor()
        assert success is True
    
    def test_doctor_healthy_symlinks(self, doti_instance, test_file):
        """Test doctor with healthy symlinks"""
        doti_instance.add_file(str(test_file))
        
        success = doti_instance.doctor()
        assert success is True
    
    def test_doctor_broken_symlinks(self, doti_instance, test_file):
        """Test doctor with broken symlinks"""
        doti_instance.add_file(str(test_file))
        
        # Break the symlink
        test_file.unlink()
        
        success = doti_instance.doctor()
        assert success is False


class TestDotiHooks:
    """Test hook functionality"""
    
    def test_run_hook_nonexistent(self, doti_instance):
        """Test running non-existent hook"""
        success = doti_instance.run_hook("nonexistent-hook")
        assert success is True  # Should not fail for non-existent hooks
    
    def test_run_hook_dry_run(self, doti_instance):
        """Test running hook in dry-run mode"""
        success = doti_instance.run_hook("test-hook", dry_run=True)
        assert success is True
