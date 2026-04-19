import pytest


# ── Valid test data ──────────────────────────────────────────────────────────
VALID_USER = {"email": "test@test.com", "username": "testuser", "password": "password123"}


# ── Registration ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post("/api/v1/auth/register", json=VALID_USER)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@test.com"
    assert data["username"] == "testuser"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/v1/auth/register", json=VALID_USER)
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "other_user",
        "password": "password123",
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    await client.post("/api/v1/auth/register", json=VALID_USER)
    response = await client.post("/api/v1/auth/register", json={
        "email": "other@test.com",
        "username": "testuser",
        "password": "password123",
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_missing_fields(client):
    response = await client.post("/api/v1/auth/register", json={"email": "test@test.com"})
    assert response.status_code == 422


# ── Registration: Input Validation ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_password_too_short(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "testuser",
        "password": "short",  # < 8 chars
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_too_long(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "testuser",
        "password": "a" * 129,  # > 128 chars
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_username_too_short(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "ab",  # < 3 chars
        "password": "password123",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_username_too_long(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "a" * 31,  # > 30 chars
        "password": "password123",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "username": "testuser",
        "password": "password123",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_exactly_8_chars(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "testuser",
        "password": "12345678",  # exactly 8 — should pass
    })
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_register_username_exactly_3_chars(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "abc",  # exactly 3 — should pass
        "password": "password123",
    })
    assert response.status_code == 200


# ── Login ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json=VALID_USER)
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json=VALID_USER)
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_nonexistent_email(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "password123",
    })
    assert response.status_code == 400


# ── Protected Route: /me ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_with_valid_token(client):
    await client.post("/api/v1/auth/register", json=VALID_USER)
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "password123",
    })
    token = login_res.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@test.com"
    assert response.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_me_without_token(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(client):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken123"},
    )
    assert response.status_code == 401


# ── Logout ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out"