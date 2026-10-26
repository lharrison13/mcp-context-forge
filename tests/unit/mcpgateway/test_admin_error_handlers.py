# -*- coding: utf-8 -*-
"""Location: ./tests/unit/mcpgateway/test_admin_error_handlers.py
Copyright contributors to the MCP-CONTEXT-FORGE project
SPDX-License-Identifier: Apache-2.0

Tests for error handling paths in admin.py to improve coverage.
"""

# Standard
from unittest.mock import AsyncMock, MagicMock, patch

# Third-Party
from pydantic_core import ValidationError as CoreValidationError
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# First-Party
from mcpgateway.services.server_service import ServerError, ServerNameConflictError


class FakeForm(dict):
    """Fake form class for testing."""

    def getlist(self, key, default=None):
        value = self.get(key, default)
        if isinstance(value, list):
            return value
        if value is None:
            return default or []
        return [value]


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock()
    request.scope = {"root_path": ""}
    request.form = AsyncMock(
        return_value=FakeForm(
            {
                "name": "test_server",
                "description": "Test description",
                "icon": "http://example.com/icon.png",
                "associatedTools": ["550e8400e29b41d4a716446655440001", "550e8400e29b41d4a716446655440002"],  # pragma: allowlist secret
                "associatedResources": ["550e8400e29b41d4a716446655440003"],  # pragma: allowlist secret
                "associatedPrompts": ["550e8400e29b41d4a716446655440004"],  # pragma: allowlist secret
                "is_inactive_checked": "false",
                "visibility": "private",
            }
        )
    )
    request.query_params = {"include_inactive": "false"}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "test-agent"}
    return request


@pytest.fixture
def mock_user():
    """Create a mock user."""
    return {"email": "test_user@example.com", "full_name": "Test User", "is_admin": True}


@pytest.fixture
def allow_permission(monkeypatch):
    """Allow RBAC permission checks to pass."""
    mock_perm_service = MagicMock()
    mock_perm_service.check_permission = AsyncMock(return_value=True)
    monkeypatch.setattr("mcpgateway.middleware.rbac.PermissionService", lambda db: mock_perm_service)
    monkeypatch.setattr("mcpgateway.plugins.get_plugin_manager", AsyncMock(return_value=None))
    return mock_perm_service


class TestAdminAddServerErrors:
    """Tests for error handling in admin_add_server."""

    @pytest.mark.asyncio
    async def test_admin_add_server_core_validation_error(self, mock_request, mock_db, mock_user, allow_permission):
        """Test CoreValidationError handling in admin_add_server."""
        # First-Party
        from mcpgateway.admin import admin_add_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_svc_instance = MagicMock()
            mock_team_svc_instance.verify_team_for_user = AsyncMock(return_value=None)
            mock_team_service.return_value = mock_team_svc_instance

            mock_service.register_server = AsyncMock(side_effect=CoreValidationError.from_exception_data("test", []))

            response = await admin_add_server(mock_request, mock_db, user=mock_user)
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_admin_add_server_name_conflict_error(self, mock_request, mock_db, mock_user, allow_permission):
        """Test ServerNameConflictError handling in admin_add_server."""
        # First-Party
        from mcpgateway.admin import admin_add_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_svc_instance = MagicMock()
            mock_team_svc_instance.verify_team_for_user = AsyncMock(return_value=None)
            mock_team_service.return_value = mock_team_svc_instance

            mock_service.register_server = AsyncMock(side_effect=ServerNameConflictError("Name conflict"))

            response = await admin_add_server(mock_request, mock_db, user=mock_user)
            assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_admin_add_server_server_error(self, mock_request, mock_db, mock_user, allow_permission):
        """Test ServerError handling in admin_add_server."""
        # First-Party
        from mcpgateway.admin import admin_add_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_svc_instance = MagicMock()
            mock_team_svc_instance.verify_team_for_user = AsyncMock(return_value=None)
            mock_team_service.return_value = mock_team_svc_instance

            mock_service.register_server = AsyncMock(side_effect=ServerError("Server error"))

            response = await admin_add_server(mock_request, mock_db, user=mock_user)
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_admin_add_server_value_error(self, mock_request, mock_db, mock_user, allow_permission):
        """Test ValueError handling in admin_add_server."""
        # First-Party
        from mcpgateway.admin import admin_add_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_svc_instance = MagicMock()
            mock_team_svc_instance.verify_team_for_user = AsyncMock(return_value=None)
            mock_team_service.return_value = mock_team_svc_instance

            mock_service.register_server = AsyncMock(side_effect=ValueError("Invalid value"))

            response = await admin_add_server(mock_request, mock_db, user=mock_user)
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_admin_add_server_integrity_error(self, mock_request, mock_db, mock_user, allow_permission):
        """Test IntegrityError handling in admin_add_server."""
        # First-Party
        from mcpgateway.admin import admin_add_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_svc_instance = MagicMock()
            mock_team_svc_instance.verify_team_for_user = AsyncMock(return_value=None)
            mock_team_service.return_value = mock_team_svc_instance

            mock_error = IntegrityError("INSERT failed", {}, Exception("constraint violation"))
            mock_service.register_server = AsyncMock(side_effect=mock_error)

            response = await admin_add_server(mock_request, mock_db, user=mock_user)
            assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_admin_add_server_unexpected_error(self, mock_request, mock_db, mock_user, allow_permission):
        """Test unexpected exception handling in admin_add_server."""
        # First-Party
        from mcpgateway.admin import admin_add_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_svc_instance = MagicMock()
            mock_team_svc_instance.verify_team_for_user = AsyncMock(return_value=None)
            mock_team_service.return_value = mock_team_svc_instance

            mock_service.register_server = AsyncMock(side_effect=Exception("Unknown error"))

            response = await admin_add_server(mock_request, mock_db, user=mock_user)
            assert response.status_code == 500


class TestAdminEditServerErrors:
    """Tests for error handling in admin_edit_server."""

    @pytest.fixture
    def mock_edit_request(self):
        """Create a mock request for edit operations."""
        request = MagicMock()
        request.scope = {"root_path": ""}
        request.form = AsyncMock(
            return_value=FakeForm(
                {
                    "name": "updated_server",
                    "description": "Updated description",
                    "icon": "http://example.com/icon.png",
                    "associatedTools": ["550e8400e29b41d4a716446655440001"],  # pragma: allowlist secret
                    "associatedResources": [],
                    "associatedPrompts": [],
                    "is_inactive_checked": "false",
                    "visibility": "private",
                }
            )
        )
        request.query_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent"}
        return request

    @pytest.mark.asyncio
    async def test_admin_edit_server_name_conflict(self, mock_edit_request, mock_db, mock_user, allow_permission):
        """Test ServerNameConflictError handling in admin_edit_server."""
        # First-Party
        from mcpgateway.admin import admin_edit_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_svc_instance = MagicMock()
            mock_team_svc_instance.verify_team_for_user = AsyncMock(return_value=None)
            mock_team_service.return_value = mock_team_svc_instance

            mock_service.update_server = AsyncMock(side_effect=ServerNameConflictError("Name conflict"))

            response = await admin_edit_server("test-id", mock_edit_request, mock_db, user=mock_user)
            assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_admin_edit_server_permission_error(self, mock_edit_request, mock_db, mock_user, allow_permission):
        """Test PermissionError handling in admin_edit_server."""
        # First-Party
        from mcpgateway.admin import admin_edit_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_svc_instance = MagicMock()
            mock_team_svc_instance.verify_team_for_user = AsyncMock(return_value=None)
            mock_team_service.return_value = mock_team_svc_instance

            mock_service.update_server = AsyncMock(side_effect=PermissionError("Not authorized"))

            response = await admin_edit_server("test-id", mock_edit_request, mock_db, user=mock_user)
            assert response.status_code == 403

    @staticmethod
    def _oauth_edit_request(mock_edit_request):
        mock_edit_request.form = AsyncMock(
            return_value=FakeForm(
                {
                    "name": "updated_server",
                    "visibility": "private",
                    "oauth_enabled": "on",
                    "oauth_authorization_servers": "https://attacker.example.com",
                }
            )
        )
        return mock_edit_request

    @pytest.mark.asyncio
    async def test_admin_edit_server_oauth_denied_without_update_permission(self, mock_edit_request, mock_db, mock_user, monkeypatch):
        """A caller without servers.update is denied before the stored oauth_config is read or merged."""
        # Third-Party
        from fastapi import HTTPException

        # First-Party
        from mcpgateway.admin import admin_edit_server

        deny_service = MagicMock()
        deny_service.check_permission = AsyncMock(return_value=False)
        monkeypatch.setattr("mcpgateway.middleware.rbac.PermissionService", lambda db: deny_service)
        monkeypatch.setattr("mcpgateway.plugins.get_plugin_manager", AsyncMock(return_value=None))
        stored_config = {"authorization_servers": ["https://idp.example.com"], "resource": "aud"}
        mock_db.get.return_value = MagicMock(team_id="team-1", oauth_config=dict(stored_config))

        with patch("mcpgateway.admin.server_service") as mock_service:
            mock_service.update_server = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await admin_edit_server("test-id", self._oauth_edit_request(mock_edit_request), mock_db, user={**mock_user, "is_admin": False})

        assert exc_info.value.status_code == 403
        mock_service.update_server.assert_not_awaited()
        mock_db.get.assert_not_called()
        assert mock_db.get.return_value.oauth_config == stored_config

    @pytest.mark.asyncio
    async def test_admin_edit_server_oauth_wrong_team_leaves_config_unchanged(self, mock_edit_request, mock_db, mock_user, allow_permission):
        """A wrong-team ownership denial from update_server returns 403 without echoing or storing the merged config."""
        # First-Party
        from mcpgateway.admin import admin_edit_server

        stored_config = {"authorization_servers": ["https://idp.example.com"], "client_id": "cid"}
        stored_server = MagicMock(team_id="other-team", oauth_config=dict(stored_config))
        mock_db.get.return_value = stored_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_service.return_value.verify_team_for_user = AsyncMock(return_value="other-team")
            mock_service.update_server = AsyncMock(side_effect=PermissionError("Only the owner can update this server"))

            response = await admin_edit_server("test-id", self._oauth_edit_request(mock_edit_request), mock_db, user=mock_user)

        assert response.status_code == 403
        assert b"attacker.example.com" not in response.body
        assert b"cid" not in response.body
        assert stored_server.oauth_config == stored_config
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_edit_server_runtime_error(self, mock_edit_request, mock_db, mock_user, allow_permission):
        """Test RuntimeError handling in admin_edit_server."""
        # First-Party
        from mcpgateway.admin import admin_edit_server

        with (
            patch("mcpgateway.admin.server_service") as mock_service,
            patch("mcpgateway.admin.TeamManagementService") as mock_team_service,
        ):
            mock_team_svc_instance = MagicMock()
            mock_team_svc_instance.verify_team_for_user = AsyncMock(return_value=None)
            mock_team_service.return_value = mock_team_svc_instance

            mock_service.update_server = AsyncMock(side_effect=RuntimeError("Runtime error"))

            response = await admin_edit_server("test-id", mock_edit_request, mock_db, user=mock_user)
            assert response.status_code == 500
