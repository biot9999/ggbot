"""Tests for utility functions."""
import os
import tempfile
from pathlib import Path

import pytest


class TestHelpers:
    """Test helper functions."""

    def test_parse_target_identifier_username(self):
        """Test parsing username identifier."""
        from src.utils.helpers import parse_target_identifier
        
        identifier, id_type = parse_target_identifier("@testuser")
        assert identifier == "testuser"
        assert id_type == "username"
        
        identifier, id_type = parse_target_identifier("testuser")
        assert identifier == "testuser"
        assert id_type == "username"

    def test_parse_target_identifier_user_id(self):
        """Test parsing user ID identifier."""
        from src.utils.helpers import parse_target_identifier
        
        identifier, id_type = parse_target_identifier("123456789")
        assert identifier == "123456789"
        assert id_type == "user_id"

    def test_parse_target_identifier_phone(self):
        """Test parsing phone number identifier."""
        from src.utils.helpers import parse_target_identifier
        
        identifier, id_type = parse_target_identifier("+1234567890123")
        assert identifier == "+1234567890123"
        assert id_type == "phone"

    def test_deduplicate_targets(self):
        """Test target deduplication."""
        from src.utils.helpers import deduplicate_targets
        
        targets = [
            ("user1", "username"),
            ("user2", "username"),
            ("user1", "username"),
            ("123456", "user_id"),
            ("123456", "user_id"),
        ]
        
        result = deduplicate_targets(targets)
        assert len(result) == 3
        assert ("user1", "username") in result
        assert ("user2", "username") in result
        assert ("123456", "user_id") in result

    def test_render_template(self):
        """Test template rendering."""
        from src.utils.helpers import render_template
        
        template = "Hello {username}! Your ID is {user_id}."
        variables = {
            "username": "testuser",
            "user_id": "12345",
        }
        
        result = render_template(template, variables)
        assert result == "Hello testuser! Your ID is 12345."

    def test_render_template_missing_variable(self):
        """Test template rendering with missing variable."""
        from src.utils.helpers import render_template
        
        template = "Hello {username}! Your ID is {user_id}."
        variables = {
            "username": "testuser",
        }
        
        result = render_template(template, variables)
        assert "{user_id}" in result  # Should keep unresolved variable

    def test_load_target_list(self):
        """Test loading target list from file."""
        from src.utils.helpers import load_target_list
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("@user1\n")
            f.write("user2\n")
            f.write("# comment line\n")
            f.write("123456789\n")
            f.write("+1234567890123\n")
            temp_path = f.name
        
        try:
            targets = load_target_list(Path(temp_path))
            assert len(targets) == 4
            assert ("user1", "username") in targets
            assert ("user2", "username") in targets
            assert ("123456789", "user_id") in targets
            assert ("+1234567890123", "phone") in targets
        finally:
            os.unlink(temp_path)

    def test_format_file_size(self):
        """Test file size formatting."""
        from src.utils.helpers import format_file_size
        
        assert format_file_size(500) == "500.0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"


class TestModels:
    """Test data models."""

    def test_account_to_dict(self):
        """Test Account to_dict method."""
        from src.models import Account, AccountStatus
        
        account = Account(
            session_file="test.session",
            phone="+1234567890",
            user_id=12345,
            username="testuser",
            status=AccountStatus.ACTIVE,
        )
        
        data = account.to_dict()
        assert data["session_file"] == "test.session"
        assert data["phone"] == "+1234567890"
        assert data["user_id"] == 12345
        assert data["username"] == "testuser"
        assert data["status"] == "active"

    def test_account_from_dict(self):
        """Test Account from_dict method."""
        from src.models import Account, AccountStatus
        
        data = {
            "session_file": "test.session",
            "phone": "+1234567890",
            "user_id": 12345,
            "username": "testuser",
            "status": "active",
        }
        
        account = Account.from_dict(data)
        assert account.session_file == "test.session"
        assert account.phone == "+1234567890"
        assert account.user_id == 12345
        assert account.username == "testuser"
        assert account.status == AccountStatus.ACTIVE

    def test_proxy_connection_string(self):
        """Test Proxy connection string generation."""
        from src.models import Proxy, ProxyType
        
        proxy = Proxy(
            id="test123",
            proxy_type=ProxyType.SOCKS5,
            host="127.0.0.1",
            port=1080,
        )
        
        assert proxy.get_connection_string() == "socks5://127.0.0.1:1080"
        
        proxy_with_auth = Proxy(
            id="test456",
            proxy_type=ProxyType.HTTP,
            host="proxy.example.com",
            port=8080,
            username="user",
            password="pass",
        )
        
        assert proxy_with_auth.get_connection_string() == "http://user:pass@proxy.example.com:8080"

    def test_send_task_progress_text(self):
        """Test SendTask progress text generation."""
        from src.models import SendTask, TaskStatus
        
        task = SendTask(
            id="task123",
            name="Test Task",
            template_id="tpl123",
            target_list_file="targets.txt",
            accounts=["session1.session"],
            total_targets=100,
            sent_count=50,
            success_count=45,
            failed_count=3,
            skipped_count=2,
        )
        
        progress = task.get_progress_text()
        assert "50.0%" in progress
        assert "50/100" in progress
        assert "45" in progress  # success
        assert "3" in progress   # failed
        assert "2" in progress   # skipped


class TestTargetUser:
    """Test TargetUser model."""

    def test_target_user_to_dict(self):
        """Test TargetUser to_dict method."""
        from src.models import TargetUser
        
        target = TargetUser(
            identifier="testuser",
            identifier_type="username",
            user_id=12345,
            username="testuser",
            is_valid=True,
        )
        
        data = target.to_dict()
        assert data["identifier"] == "testuser"
        assert data["identifier_type"] == "username"
        assert data["user_id"] == 12345
        assert data["is_valid"] is True


class TestMessageTemplate:
    """Test MessageTemplate model."""

    def test_message_template_to_dict(self):
        """Test MessageTemplate to_dict method."""
        from src.models import MessageTemplate
        
        template = MessageTemplate(
            id="tpl123",
            name="Test Template",
            text="Hello {username}!",
            buttons=[{"text": "Click", "url": "https://example.com"}],
        )
        
        data = template.to_dict()
        assert data["id"] == "tpl123"
        assert data["name"] == "Test Template"
        assert data["text"] == "Hello {username}!"
        assert len(data["buttons"]) == 1

    def test_message_template_from_dict(self):
        """Test MessageTemplate from_dict method."""
        from src.models import MessageTemplate
        
        data = {
            "id": "tpl456",
            "name": "Another Template",
            "text": "Test message",
            "media_type": "photo",
            "created_at": "2024-01-01T00:00:00",
        }
        
        template = MessageTemplate.from_dict(data)
        assert template.id == "tpl456"
        assert template.name == "Another Template"
        assert template.text == "Test message"
        assert template.media_type == "photo"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
