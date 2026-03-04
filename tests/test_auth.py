import pytest

# -- Registration tests --

@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "testuser",
        "password": "test123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@test.com"
    assert data["username"] == "testuser"
    assert "id" in data
    assert "password" not in data  # password_hash should NOT be exposed


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    # Register first user
    await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "user1",
        "password": "test123",
    })
    # Try same email again
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "user2",
        "password": "test123",
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_missing_fields(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
    })
    assert response.status_code == 422  # Validation error


# -- Login tests --

@pytest.mark.asyncio
async def test_login_success(client):
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "testuser",
        "password": "test123",
    })
    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "test123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "testuser",
        "password": "test123",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_nonexistent_email(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "test123",
    })
    assert response.status_code == 400


# -- Protected route tests --

@pytest.mark.asyncio
async def test_me_with_valid_token(client):
    # Register + login
    await client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "testuser",
        "password": "test123",
    })
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "test123",
    })
    token = login_res.json()["access_token"]

    # Access protected route
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@test.com"


# @pytest.mark.asyncio
# async def test_me_without_token(client):
#     response = await client.get("/api/v1/auth/me")
#     assert response.status_code == 401


# @pytest.mark.asyncio
# async def test_me_with_invalid_token(client):
#     response = await client.get(
#         "/api/v1/auth/me",
#         headers={"Authorization": "Bearer invalidtoken123"},
#     )
#     assert response.status_code == 401