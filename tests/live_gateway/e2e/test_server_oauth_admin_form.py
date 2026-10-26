# -*- coding: utf-8 -*-
"""Location: ./tests/live_gateway/e2e/test_server_oauth_admin_form.py
Copyright contributors to the MCP-CONTEXT-FORGE project
SPDX-License-Identifier: Apache-2.0

Live-gateway regression for the virtual-server OAuth Admin UI form (issue #7338).

The unit suite drives the form helpers directly. These tests prove the same
behavior through the running HTTP boundary:

1. An Edit form save with the prefilled OAuth values keeps the API-set
   ``authorization_servers``, ``resource``, and ``scopes_supported``.
2. The Add form stores several authorization servers and a resource.
3. An unauthenticated Edit form post returns 401 and leaves ``oauth_config`` unchanged.
"""

# Future
from __future__ import annotations

# Standard
from collections.abc import Iterator
import os
import subprocess
import sys
import uuid

# Third-Party
import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration (mirrors helpers/mcp_test_helpers.py)
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("MCP_CLI_BASE_URL", "http://127.0.0.1:8080").replace("//localhost", "//127.0.0.1")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "my-test-key-but-now-longer-than-32-bytes")
ADMIN_EMAIL = os.getenv("PLATFORM_ADMIN_EMAIL", "admin@example.com")
TOKEN_EXPIRY = os.getenv("MCP_CLI_TOKEN_EXPIRY", "60")

AUTHORIZATION_SERVERS = ["https://shim.example.com", "https://tenant.verify.ibm.com/oidc/endpoint/default"]
RESOURCE = "agent-client-id"
SCOPES = ["openid", "profile"]


def _gateway_reachable() -> bool:
    try:
        return httpx.get(f"{BASE_URL}/health", timeout=5).status_code == 200
    except Exception:
        return False


skip_no_gateway = pytest.mark.skipif(not _gateway_reachable(), reason=f"Gateway not reachable at {BASE_URL}")


@pytest.fixture(scope="module")
def jwt_token() -> str:
    """Generate a short-lived admin JWT for the test module."""
    result = subprocess.run(
        [sys.executable, "-m", "mcpgateway.utils.create_jwt_token", "--username", ADMIN_EMAIL, "--admin", "--exp", TOKEN_EXPIRY, "--secret", JWT_SECRET],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
        env={**os.environ, "JWT_SECRET_KEY": JWT_SECRET},
    )
    assert result.returncode == 0, f"JWT generation failed: {result.stderr}"
    # ``--admin`` prints a development-only warning before the token; the token is the last line.
    return result.stdout.strip().splitlines()[-1].strip('"')


@pytest.fixture(scope="module")
def auth_headers(jwt_token: str) -> dict[str, str]:
    """Return the Authorization header dict."""
    return {"Authorization": f"Bearer {jwt_token}"}


def _server_name() -> str:
    return f"oauth-form-{uuid.uuid4().hex[:8]}"


def _get_oauth_config(server_id: str, auth_headers: dict[str, str]) -> dict:
    resp = httpx.get(f"{BASE_URL}/servers/{server_id}", headers=auth_headers, timeout=15)
    assert resp.status_code == 200, f"GET /servers/{server_id} failed: {resp.status_code} {resp.text}"
    body = resp.json()
    return body.get("oauthConfig") or body.get("oauth_config") or {}


def _skip_if_admin_api_disabled(resp: httpx.Response) -> None:
    if resp.status_code == 404:
        pytest.skip("Admin API is disabled on this gateway (MCPGATEWAY_ADMIN_API_ENABLED=false)")


@pytest.fixture
def api_server(auth_headers: dict[str, str]) -> Iterator[dict]:
    """Create a server with an API-set OAuth config and delete it afterwards."""
    name = _server_name()
    resp = httpx.post(
        f"{BASE_URL}/servers",
        json={
            "server": {
                "name": name,
                "description": "before",
                "oauth_enabled": True,
                "oauth_config": {"authorization_servers": AUTHORIZATION_SERVERS, "resource": RESOURCE, "scopes_supported": SCOPES},
            },
            "visibility": "private",
        },
        headers=auth_headers,
        timeout=15,
    )
    assert resp.status_code == 201, f"POST /servers failed: {resp.status_code} {resp.text}"
    server = resp.json()
    yield server
    httpx.delete(f"{BASE_URL}/servers/{server['id']}", headers=auth_headers, timeout=15)


def _prefilled_edit_form(server: dict, description: str) -> dict[str, str]:
    """Return the form fields the Edit Server modal posts after prefill."""
    return {
        "name": server["name"],
        "description": description,
        "visibility": "private",
        "oauth_enabled": "on",
        "oauth_authorization_servers": "\n".join(AUTHORIZATION_SERVERS),
        "oauth_scopes": " ".join(SCOPES),
        "oauth_token_endpoint": "",
        "oauth_resource": RESOURCE,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@skip_no_gateway
def test_unrelated_edit_keeps_api_set_oauth_keys(api_server: dict, auth_headers: dict[str, str]):
    """An Edit form save that only changes the description keeps every API-set OAuth key."""
    resp = httpx.post(
        f"{BASE_URL}/admin/servers/{api_server['id']}/edit",
        data=_prefilled_edit_form(api_server, "after"),
        headers={**auth_headers, "Accept": "application/json"},
        timeout=15,
    )
    _skip_if_admin_api_disabled(resp)
    assert resp.status_code == 200, f"Edit form save failed: {resp.status_code} {resp.text}"

    oauth_config = _get_oauth_config(api_server["id"], auth_headers)
    assert oauth_config.get("authorization_servers") == AUTHORIZATION_SERVERS
    assert oauth_config.get("resource") == RESOURCE
    assert oauth_config.get("scopes_supported") == SCOPES


@skip_no_gateway
def test_add_form_stores_multiple_authorization_servers_and_resource(auth_headers: dict[str, str]):
    """The Add form stores several authorization servers and a resource."""
    server_id = uuid.uuid4().hex
    resp = httpx.post(
        f"{BASE_URL}/admin/servers",
        data={
            "id": server_id,
            "name": _server_name(),
            "visibility": "private",
            "oauth_enabled": "on",
            "oauth_authorization_servers": "\n".join(AUTHORIZATION_SERVERS),
            "oauth_resource": RESOURCE,
        },
        headers={**auth_headers, "Accept": "application/json"},
        timeout=15,
    )
    _skip_if_admin_api_disabled(resp)
    try:
        assert resp.status_code == 200, f"Add form save failed: {resp.status_code} {resp.text}"

        oauth_config = _get_oauth_config(server_id, auth_headers)
        assert oauth_config.get("authorization_servers") == AUTHORIZATION_SERVERS
        assert oauth_config.get("resource") == RESOURCE
    finally:
        httpx.delete(f"{BASE_URL}/servers/{server_id}", headers=auth_headers, timeout=15)


@skip_no_gateway
def test_unauthenticated_edit_is_rejected_and_keeps_oauth_config(api_server: dict, auth_headers: dict[str, str]):
    """An unauthenticated Edit form post returns 401 and does not touch the stored OAuth config."""
    form = _prefilled_edit_form(api_server, "after")
    form["oauth_authorization_servers"] = "https://attacker.example.com"
    form["oauth_resource"] = ""
    resp = httpx.post(
        f"{BASE_URL}/admin/servers/{api_server['id']}/edit",
        data=form,
        headers={"Accept": "application/json"},
        timeout=15,
    )
    _skip_if_admin_api_disabled(resp)
    assert resp.status_code == 401, f"Expected 401 for unauthenticated edit, got {resp.status_code}: {resp.text}"

    oauth_config = _get_oauth_config(api_server["id"], auth_headers)
    assert oauth_config.get("authorization_servers") == AUTHORIZATION_SERVERS
    assert oauth_config.get("resource") == RESOURCE
