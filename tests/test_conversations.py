import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

async def register_and_login(client, email: str, username: str, password: str = "test123") -> str:
    """Register a user and return their access token."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "username": username,
        "password": password,
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    return res.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Create Conversation ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_conversation_success(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    response = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Test Group", "member_ids": []},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Group"
    assert data["type"] == "group"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_conversation_no_title(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    response = await client.post(
        "/api/v1/conversations/",
        json={"type": "direct", "member_ids": []},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json()["title"] is None


@pytest.mark.asyncio
async def test_create_conversation_unauthenticated(client):
    response = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Test", "member_ids": []},
    )
    assert response.status_code == 401


# ── List Conversations ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_conversations_empty(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    response = await client.get("/api/v1/conversations/", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_conversations_shows_own(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "My Group", "member_ids": []},
        headers=auth_header(token),
    )
    response = await client.get("/api/v1/conversations/", headers=auth_header(token))
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "My Group"


@pytest.mark.asyncio
async def test_list_conversations_only_own(client):
    """User should only see conversations they are a member of."""
    token1 = await register_and_login(client, "user1@test.com", "user1")
    token2 = await register_and_login(client, "user2@test.com", "user2")

    # user1 creates a conversation, user2 is not added
    await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Secret Group", "member_ids": []},
        headers=auth_header(token1),
    )

    response = await client.get("/api/v1/conversations/", headers=auth_header(token2))
    assert response.status_code == 200
    assert response.json() == []


# ── Get Single Conversation ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_conversation_success(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Test", "member_ids": []},
        headers=auth_header(token),
    )
    conv_id = create_res.json()["id"]

    response = await client.get(f"/api/v1/conversations/{conv_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["id"] == conv_id


@pytest.mark.asyncio
async def test_get_conversation_not_member(client):
    token1 = await register_and_login(client, "user1@test.com", "user1")
    token2 = await register_and_login(client, "user2@test.com", "user2")

    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Private", "member_ids": []},
        headers=auth_header(token1),
    )
    conv_id = create_res.json()["id"]

    response = await client.get(f"/api/v1/conversations/{conv_id}", headers=auth_header(token2))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_conversation_not_found(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    response = await client.get("/api/v1/conversations/999", headers=auth_header(token))
    assert response.status_code == 404


# ── Add Member ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_member_success(client):
    token1 = await register_and_login(client, "user1@test.com", "user1")
    res2 = await client.post("/api/v1/auth/register", json={
        "email": "user2@test.com", "username": "user2", "password": "test123"
    })
    user2_id = res2.json()["id"]

    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Group", "member_ids": []},
        headers=auth_header(token1),
    )
    conv_id = create_res.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/members",
        json={"user_id": user2_id},
        headers=auth_header(token1),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Member added"


@pytest.mark.asyncio
async def test_add_member_not_allowed_if_not_member(client):
    token1 = await register_and_login(client, "user1@test.com", "user1")
    token2 = await register_and_login(client, "user2@test.com", "user2")

    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Private", "member_ids": []},
        headers=auth_header(token1),
    )
    conv_id = create_res.json()["id"]

    # user2 tries to add someone to a conversation they're not in
    response = await client.post(
        f"/api/v1/conversations/{conv_id}/members",
        json={"user_id": 999},
        headers=auth_header(token2),
    )
    assert response.status_code == 403


# ── Send Message ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_message_success(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Chat", "member_ids": []},
        headers=auth_header(token),
    )
    conv_id = create_res.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Hello world!"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Hello world!"
    assert data["conversation_id"] == conv_id
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_send_message_not_member(client):
    token1 = await register_and_login(client, "user1@test.com", "user1")
    token2 = await register_and_login(client, "user2@test.com", "user2")

    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Private", "member_ids": []},
        headers=auth_header(token1),
    )
    conv_id = create_res.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Intruder!"},
        headers=auth_header(token2),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_send_message_unauthenticated(client):
    response = await client.post(
        "/api/v1/conversations/1/messages",
        json={"content": "Hello"},
    )
    assert response.status_code == 401


# ── Get Messages ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_messages_empty(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Chat", "member_ids": []},
        headers=auth_header(token),
    )
    conv_id = create_res.json()["id"]

    response = await client.get(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_messages_returns_sent(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Chat", "member_ids": []},
        headers=auth_header(token),
    )
    conv_id = create_res.json()["id"]

    # Send 3 messages
    for i in range(1, 4):
        await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": f"Message {i}"},
            headers=auth_header(token),
        )

    response = await client.get(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 3
    assert messages[0]["content"] == "Message 1"
    assert messages[2]["content"] == "Message 3"


@pytest.mark.asyncio
async def test_get_messages_pagination(client):
    token = await register_and_login(client, "user1@test.com", "user1")
    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Chat", "member_ids": []},
        headers=auth_header(token),
    )
    conv_id = create_res.json()["id"]

    # Send 5 messages
    for i in range(1, 6):
        await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": f"Message {i}"},
            headers=auth_header(token),
        )

    # Get first 2
    res1 = await client.get(
        f"/api/v1/conversations/{conv_id}/messages?limit=2&offset=0",
        headers=auth_header(token),
    )
    assert len(res1.json()) == 2
    assert res1.json()[0]["content"] == "Message 1"

    # Get next 2
    res2 = await client.get(
        f"/api/v1/conversations/{conv_id}/messages?limit=2&offset=2",
        headers=auth_header(token),
    )
    assert len(res2.json()) == 2
    assert res2.json()[0]["content"] == "Message 3"


@pytest.mark.asyncio
async def test_get_messages_not_member(client):
    token1 = await register_and_login(client, "user1@test.com", "user1")
    token2 = await register_and_login(client, "user2@test.com", "user2")

    create_res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": "Private", "member_ids": []},
        headers=auth_header(token1),
    )
    conv_id = create_res.json()["id"]

    response = await client.get(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=auth_header(token2),
    )
    assert response.status_code == 403
