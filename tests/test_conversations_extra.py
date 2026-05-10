import pytest
from datetime import datetime, timezone, timedelta


# ── Helpers ──────────────────────────────────────────────────────────────────

async def register_and_login(client, email: str, username: str, password: str = "password123") -> str:
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


async def create_conv(client, token: str, title: str = "Chat") -> int:
    res = await client.post(
        "/api/v1/conversations/",
        json={"type": "group", "title": title, "member_ids": []},
        headers=auth_header(token),
    )
    return res.json()["id"]


# ── Mark Conversation as Read ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_read_success(client):
    token = await register_and_login(client, "reader@test.com", "reader")
    conv_id = await create_conv(client, token, "ReadTest")

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/read",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Conversation marked as read"


@pytest.mark.asyncio
async def test_mark_read_not_member_returns_403(client):
    token1 = await register_and_login(client, "owner@test.com", "owner")
    token2 = await register_and_login(client, "stranger@test.com", "stranger")

    conv_id = await create_conv(client, token1, "Private")

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/read",
        headers=auth_header(token2),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mark_read_unauthenticated_returns_401(client):
    response = await client.post("/api/v1/conversations/1/read")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mark_read_idempotent(client):
    """Marking the same conversation read twice must not error."""
    token = await register_and_login(client, "idem@test.com", "idem")
    conv_id = await create_conv(client, token)

    res1 = await client.post(f"/api/v1/conversations/{conv_id}/read", headers=auth_header(token))
    res2 = await client.post(f"/api/v1/conversations/{conv_id}/read", headers=auth_header(token))
    assert res1.status_code == 200
    assert res2.status_code == 200


# ── Get Messages with `since` Query Parameter ─────────────────────────────────

@pytest.mark.asyncio
async def test_get_messages_since_valid_timestamp(client):
    token = await register_and_login(client, "since@test.com", "since_user")
    conv_id = await create_conv(client, token, "SinceChat")

    # Send a message before the anchor timestamp
    await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "before"},
        headers=auth_header(token),
    )

    anchor = datetime.now(timezone.utc)
    # Use the Z format to avoid URL-encoding issues with the '+' in '+00:00'
    anchor_str = anchor.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"

    # Send messages after the anchor
    for i in range(1, 3):
        await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": f"after {i}"},
            headers=auth_header(token),
        )

    response = await client.get(
        f"/api/v1/conversations/{conv_id}/messages?since={anchor_str}",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    messages = response.json()
    # Only messages strictly after the anchor should appear
    assert all("after" in m["content"] for m in messages)


@pytest.mark.asyncio
async def test_get_messages_since_z_suffix(client):
    """Timestamps ending with 'Z' must be accepted."""
    token = await register_and_login(client, "zsuffix@test.com", "zsuffix_user")
    conv_id = await create_conv(client, token, "ZChat")

    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "hello"},
        headers=auth_header(token),
    )

    response = await client.get(
        f"/api/v1/conversations/{conv_id}/messages?since={past}",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_get_messages_since_invalid_timestamp_returns_400(client):
    token = await register_and_login(client, "badts@test.com", "badts_user")
    conv_id = await create_conv(client, token, "TSChat")

    response = await client.get(
        f"/api/v1/conversations/{conv_id}/messages?since=not-a-timestamp",
        headers=auth_header(token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_messages_since_future_returns_empty(client):
    """A `since` far in the future should return no messages."""
    token = await register_and_login(client, "future@test.com", "future_user")
    conv_id = await create_conv(client, token, "FutureChat")

    await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "old message"},
        headers=auth_header(token),
    )

    future = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    response = await client.get(
        f"/api/v1/conversations/{conv_id}/messages?since={future}",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json() == []


# ── Add Member Edge Cases ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_member_to_nonexistent_conversation(client):
    """Adding a member to a conversation that does not exist must not succeed silently."""
    token = await register_and_login(client, "ghost@test.com", "ghost_user")

    response = await client.post(
        "/api/v1/conversations/99999/members",
        json={"user_id": 1},
        headers=auth_header(token),
    )
    # The caller is not a member of a nonexistent conversation → 403
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_conversations_includes_joined_via_add_member(client):
    """A user added as a member should see the conversation in their list."""
    token1 = await register_and_login(client, "host@test.com", "host")
    reg2_res = await client.post("/api/v1/auth/register", json={
        "email": "guest@test.com", "username": "guest", "password": "password123",
    })
    user2_id = reg2_res.json()["id"]
    token2 = await register_and_login(client, "guest@test.com", "guest")

    conv_id = await create_conv(client, token1, "Shared")

    await client.post(
        f"/api/v1/conversations/{conv_id}/members",
        json={"user_id": user2_id},
        headers=auth_header(token1),
    )

    response = await client.get("/api/v1/conversations/", headers=auth_header(token2))
    assert response.status_code == 200
    ids = [c["id"] for c in response.json()]
    assert conv_id in ids


@pytest.mark.asyncio
async def test_create_dm_conversation(client):
    """Creating a DM conversation must succeed and return type 'dm'."""
    token = await register_and_login(client, "dm@test.com", "dm_user")
    response = await client.post(
        "/api/v1/conversations/",
        json={"type": "dm", "title": None, "member_ids": []},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json()["type"] == "dm"


@pytest.mark.asyncio
async def test_send_message_response_has_sender_id(client):
    """The message response must include the sender_id of the current user."""
    token = await register_and_login(client, "sender@test.com", "sender_user")
    conv_id = await create_conv(client, token, "SenderChat")

    me_res = await client.get("/api/v1/auth/me", headers=auth_header(token))
    my_id = me_res.json()["id"]

    send_res = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "check sender"},
        headers=auth_header(token),
    )
    assert send_res.status_code == 200
    assert send_res.json()["sender_id"] == my_id
