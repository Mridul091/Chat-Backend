import pytest
from app.services.auth import create_refresh_token, create_access_token


# ── Helpers ──────────────────────────────────────────────────────────────────

VALID_USER = {"email": "refresh@test.com", "username": "refreshuser", "password": "password123"}


# ── Refresh Token Endpoint ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client):
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert "missing" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client):
    client.cookies.set("refresh_token", "this.is.invalid")
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token_returns_401(client):
    """Passing an access token (not a refresh token) must be rejected."""
    reg_res = await client.post("/api/v1/auth/register", json=VALID_USER)
    user_id = reg_res.json()["id"]
    access_token = create_access_token(user_id)

    client.cookies.set("refresh_token", access_token)
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_valid_cookie_returns_new_access_token(client):
    """A valid refresh-token cookie must yield a new access_token."""
    reg_res = await client.post("/api/v1/auth/register", json=VALID_USER)
    user_id = reg_res.json()["id"]

    # httpx does not forward cookies with secure=True over HTTP, so we set
    # the token directly via create_refresh_token rather than relying on the
    # login Set-Cookie header.
    client.cookies.set("refresh_token", create_refresh_token(user_id))

    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_new_token_grants_access_to_protected_route(client):
    """New access token obtained via refresh must authenticate /me."""
    reg_res = await client.post("/api/v1/auth/register", json=VALID_USER)
    user_id = reg_res.json()["id"]

    client.cookies.set("refresh_token", create_refresh_token(user_id))

    refresh_res = await client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200
    new_token = refresh_res.json()["access_token"]

    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == VALID_USER["email"]


@pytest.mark.asyncio
async def test_refresh_with_nonexistent_user_returns_401(client):
    """Refresh token for a deleted/nonexistent user_id must return 401."""
    ghost_refresh = create_refresh_token(user_id=999999)
    client.cookies.set("refresh_token", ghost_refresh)
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
