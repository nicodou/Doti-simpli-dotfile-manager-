"""
Unit tests for doti robustness features

This module tests the new server-grade features: checksums, permissions validation,
audit logging, and atomic config writes.
"""

import json
import tempfile
import shutil
import stat
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

from doti.core import Doti


class TestChecksumCalculation:
    """Test SHA-256 checksum calculation"""
    
    def test_calculate_sha256_basic(self, doti_instance, test_file):
        """Test basic SHA-256 calculation"""
        checksum = doti_instance._calculate_sha256(test_file)
        
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex length
        assert all(c in '0123456789abcdef' for c in checksum)
    
    def test_calculate_sha256_consistency(self, doti_instance, test_file):
        """Test checksum calculation is consistent"""
        checksum1 = doti_instance._calculate_sha256(test_file)
        checksum2 = doti_instance._calculate_sha256(test_file)
        
        assert checksum1 == checksum2
    
    def test_calculate_sha256_different_files(self, doti_instance, temp_dir):
        """Test different files have different checksums"""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        
        file1.write_text("content1")
        file2.write_text("content2")
        
        checksum1 = doti_instance._calculate_sha256(file1)
        checksum2 = doti_instance._calculate_sha256(file2)
        
        assert checksum1 != checksum2


class TestPermissionValidation:
    """Test sensitive file permission validation"""
    
    def test_validate_safe_permissions(self, doti_instance, sensitive_file):
        """Test validation with safe permissions (600)"""
        result = doti_instance._validate_sensitive_file_permissions(sensitive_file)
        assert result is True
    
    def test_validate_unsafe_permissions(self, doti_instance, temp_dir):
        """Test validation with unsafe permissions"""
        # Create .bashrc with unsafe permissions
        bashrc = temp_dir / ".bashrc"
        bashrc.write_text("bash config")
        bashrc.chmod(0o644)  # Safe
        
        # Change to unsafe permissions
        bashrc.chmod(0o777)  # Unsafe
        
        with pytest.raises(PermissionError) as exc_info:
            doti_instance._validate_sensitive_file_permissions(bashrc)
        
        assert "Insecure permissions 777" in str(exc_info.value)
        assert ".bashrc" in str(exc_info.value)
    
    def test_validate_non_sensitive_file(self, doti_instance, test_file):
        """Test validation with non-sensitive file"""
        result = doti_instance._validate_sensitive_file_permissions(test_file)
        assert result is True  # Should pass for non-sensitive files
    
    def test_validate_sensitive_patterns(self, doti_instance, temp_dir):
        """Test various sensitive file patterns"""
        sensitive_files = [
            temp_dir / ".ssh" / "config",
            temp_dir / ".gnupg" / "gpg.conf",
            temp_dir / ".zshrc",
            temp_dir / ".vimrc",
            temp_dir / ".profile"
        ]
        
        for file_path in sensitive_files:
            file_path.parent.mkdir(exist_ok=True)
            file_path.write_text("config")
            file_path.chmod(0o777)  # Unsafe permissions
            
            with pytest.raises(PermissionError):
                doti_instance._validate_sensitive_file_permissions(file_path)


class TestAtomicConfigWrite:
    """Test atomic configuration writing"""
    
    def test_atomic_write_success(self, doti_instance, sample_config):
        """Test successful atomic write"""
        success = doti_instance._atomic_write_config(sample_config)
        
        assert success is True
        assert doti_instance.config_file.exists()
        
        # Verify content
        loaded_config = json.loads(doti_instance.config_file.read_text())
        assert loaded_config == sample_config
    
    def test_atomic_write_no_temp_file_left(self, doti_instance, sample_config):
        """Test no temporary file is left after atomic write"""
        temp_file = doti_instance.config_file.with_suffix('.tmp')
        
        doti_instance._atomic_write_config(sample_config)
        
        assert not temp_file.exists()
    
    def test_atomic_write_overwrite_existing(self, doti_instance, sample_config):
        """Test atomic write overwrites existing config"""
        # Create existing config
        existing_config = {"existing": "data"}
        doti_instance.config_file.write_text(json.dumps(existing_config))
        
        # Atomic write new config
        success = doti_instance._atomic_write_config(sample_config)
        
        assert success is True
        loaded_config = json.loads(doti_instance.config_file.read_text())
        assert loaded_config == sample_config
        assert loaded_config != existing_config


class TestAuditLogging:
    """Test audit logging functionality"""
    
    def test_audit_log_creation(self, doti_instance):
        """Test audit log entry creation"""
        doti_instance._audit_log("test_command", "success", {"file": "test.txt"})
        
        assert doti_instance.audit_file.exists()
        
        # Read and verify entry
        with open(doti_instance.audit_file) as f:
            content = f.read().strip()
            entry = json.loads(content)
            
            assert entry['command'] == "test_command"
            assert entry['result'] == "success"
            assert entry['details']['file'] == "test.txt"
            assert 'timestamp' in entry
    
    def test_audit_log_multiple_entries(self, doti_instance):
        """Test multiple audit log entries"""
        entries = [
            ("add", "success", {"file": "file1.txt"}),
            ("deploy", "success", {"count": 5}),
            ("unlink", "error", {"file": "file2.txt"})
        ]
        
        for command, result, details in entries:
            doti_instance._audit_log(command, result, details)
        
        # Read all entries
        with open(doti_instance.audit_file) as f:
            lines = f.read().strip().split('\n')
            
        assert len(lines) == 3
        
        for i, (command, result, details) in enumerate(entries):
            entry = json.loads(lines[i])
            assert entry['command'] == command
            assert entry['result'] == result
            assert entry['details'] == details
    
    def test_audit_log_append(self, doti_instance):
        """Test audit log appends to existing file"""
        # Create existing audit log
        existing_entry = {
            'timestamp': '2024-01-01T00:00:00',
            'command': 'existing',
            'result': 'success',
            'details': {}
        }
        with open(doti_instance.audit_file, 'w') as f:
            f.write(json.dumps(existing_entry) + '\n')
        
        # Add new entry
        doti_instance._audit_log("new_command", "success")
        
        # Verify both entries exist
        with open(doti_instance.audit_file) as f:
            lines = f.read().strip().split('\n')
            
        assert len(lines) == 2
        
        first_entry = json.loads(lines[0])
        second_entry = json.loads(lines[1])
        
        assert first_entry['command'] == 'existing'
        assert second_entry['command'] == 'new_command'


class TestRobustnessIntegration:
    """Integration tests for robustness features"""
    
    def test_add_file_with_checksum(self, doti_instance, test_file):
        """Test add_file includes checksum in config"""
        success = doti_instance.add_file(str(test_file))
        
        assert success is True
        
        # Check config contains checksum
        config = doti_instance._load_config()
        file_data = config[str(test_file)]
        
        assert 'sha256' in file_data
        assert 'added_at' in file_data
        assert len(file_data['sha256']) == 64
        
        # Verify checksum is correct
        expected_checksum = doti_instance._calculate_sha256(
            doti_instance.storage_dir / test_file.name
        )
        assert file_data['sha256'] == expected_checksum
    
    def test_add_file_permission_validation(self, doti_instance, temp_dir):
        """Test add_file validates permissions for sensitive files"""
        # Create sensitive file with unsafe permissions
        bashrc = temp_dir / ".bashrc"
        bashrc.write_text("bash config")
        bashrc.chmod(0o777)  # Unsafe
        
        success = doti_instance.add_file(str(bashrc))
        
        assert success is False
        assert bashrc.exists()  # File should not be moved
    
    def test_add_file_audit_logging(self, doti_instance, test_file):
        """Test add_file logs to audit"""
        success = doti_instance.add_file(str(test_file))
        
        assert success is True
        assert doti_instance.audit_file.exists()
        
        # Check audit entry
        with open(doti_instance.audit_file) as f:
            entry = json.loads(f.read().strip())
            
        assert entry['command'] == 'add'
        assert entry['result'] == 'success'
        assert 'file_path' in entry['details']
        assert 'sha256' in entry['details']
    
    def test_add_file_atomic_config(self, doti_instance, test_file):
        """Test add_file uses atomic config write"""
        # Mock atomic_write_config to verify it's called
        with patch.object(doti_instance, '_atomic_write_config') as mock_atomic:
            mock_atomic.return_value = True
            
            doti_instance.add_file(str(test_file))
            
            # Verify atomic write was called
            mock_atomic.assert_called_once()
            
            # Verify config data includes new fields
            call_args = mock_atomic.call_args[0][0]
            file_data = call_args[str(test_file)]
            
            assert 'sha256' in file_data
            assert 'added_at' in file_data


class TestRobustnessErrorHandling:
    """Test error handling in robustness features"""
    
    def test_permission_error_handling(self, doti_instance, temp_dir):
        """Test graceful handling of permission errors"""
        # Create sensitive file with unsafe permissions
        sensitive_file = temp_dir / ".ssh" / "config"
        sensitive_file.parent.mkdir()
        sensitive_file.write_text("ssh config")
        sensitive_file.chmod(0o777)
        
        success = doti_instance.add_file(str(sensitive_file))
        
        assert success is False
        assert not doti_instance.audit_file.exists()  # No audit entry for failure
    
    def test_audit_log_write_failure(self, doti_instance, test_file):
        """Test handling of audit log write failure"""
        # Mock audit file to raise exception
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            # Should not raise exception, should continue gracefully
            doti_instance._audit_log("test", "success")
    
    def test_atomic_write_failure_cleanup(self, doti_instance, sample_config):
        """Test cleanup of temp file on atomic write failure"""
        # Mock write to raise exception
        with patch.object(Path, 'write_text', side_effect=IOError("Disk full")):
            success = doti_instance._atomic_write_config(sample_config)
            
            assert success is False
            
            # Verify temp file is cleaned up
            temp_file = doti_instance.config_file.with_suffix('.tmp')
            assert not temp_file.exists()
