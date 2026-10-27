import logging

import pytest
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.limiter import limiter
from app.main import app
from app.services.auth import create_refresh_token


# ── Helpers ──────────────────────────────────────────────────────────────────


async def register(
    client, email: str, username: str, password: str = "password123"
) -> int:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
        },
    )
    return res.json()["id"]


async def login(client, email: str, password: str = "password123"):
    return await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )


async def register_and_login(client, email: str, username: str) -> tuple[int, str]:
    user_id = await register(client, email, username)
    res = await login(client, email)
    return user_id, res.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def create_conversation(client, token: str, type_: str, member_ids: list[int]):
    return await client.post(
        "/api/v1/conversations/",
        json={"type": type_, "title": "T", "member_ids": member_ids},
        headers=auth_header(token),
    )


def refresh_cookie(res) -> str | None:
    for header in res.headers.get_list("set-cookie"):
        if header.startswith("refresh_token="):
            return header.split(";")[0].split("=", 1)[1]
    return None


async def post_with_refresh_cookie(client, path: str, token: str):
    # The cookie is Secure, so the http test client's jar won't send it back;
    # send it explicitly and keep the jar out of the way.
    client.cookies.clear()
    return await client.post(path, headers={"Cookie": f"refresh_token={token}"})


def ws_join(tc: TestClient, conversation_id: int, token: str):
    ws = tc.websocket_connect(f"/ws/{conversation_id}")
    conn = ws.__enter__()
    conn.send_json({"token": token})
    return ws, conn


# ── 1. WebSocket: non-members cannot join a conversation ─────────────────────


@pytest.mark.asyncio
async def test_ws_non_member_is_rejected(client):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")
    _, token2 = await register_and_login(client, "u2@test.com", "user2")
    conv_id = (await create_conversation(client, token1, "group", [])).json()["id"]

    with TestClient(app) as tc:
        with tc.websocket_connect(f"/ws/{conv_id}") as ws:
            ws.send_json({"token": token2})
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_json()
            assert exc.value.code == 1008


@pytest.mark.asyncio
async def test_ws_member_can_join_and_receive_messages(client):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")
    conv_id = (await create_conversation(client, token1, "group", [])).json()["id"]

    with TestClient(app) as tc:
        with tc.websocket_connect(f"/ws/{conv_id}") as ws:
            ws.send_json({"token": token1})
            assert ws.receive_json()["type"] == "presence_state"
            assert ws.receive_json()["type"] == "user_online"
            ws.send_json({"content": "hello"})
            msg = ws.receive_json()
            assert msg["type"] == "message"
            assert msg["content"] == "hello"


# ── 2. WebSocket: presence only covers the conversation's members ────────────


@pytest.mark.asyncio
async def test_ws_presence_scoped_to_conversation(client):
    user1, token1 = await register_and_login(client, "u1@test.com", "user1")
    user2, _ = await register_and_login(client, "u2@test.com", "user2")
    _, token3 = await register_and_login(client, "u3@test.com", "user3")
    conv_a = (await create_conversation(client, token1, "group", [user2])).json()["id"]
    conv_b = (await create_conversation(client, token3, "group", [])).json()["id"]

    with TestClient(app) as tc:
        # user3 is online, but only in an unrelated conversation
        with tc.websocket_connect(f"/ws/{conv_b}") as ws3:
            ws3.send_json({"token": token3})
            ws3.receive_json()  # presence_state
            ws3.receive_json()  # user_online

            with tc.websocket_connect(f"/ws/{conv_a}") as ws1:
                ws1.send_json({"token": token1})
                presence = ws1.receive_json()
                assert presence["type"] == "presence_state"
                assert presence["online_users"] == [user1]


# ── 3. Rate limiting keys on the real client IP behind a trusted proxy ───────


@pytest.fixture
def rate_limiting():
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


async def failed_login(client, ip: str):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "wrong-password"},
        headers={"X-Forwarded-For": ip},
    )


@pytest.mark.asyncio
async def test_rate_limit_is_per_client_behind_trusted_proxy(client, rate_limiting):
    # The test transport's peer is 127.0.0.1, the default trusted proxy
    for _ in range(5):
        assert (await failed_login(client, "203.0.113.1")).status_code == 400
    assert (await failed_login(client, "203.0.113.1")).status_code == 429

    # A different client behind the same proxy has its own budget
    assert (await failed_login(client, "203.0.113.2")).status_code == 400


@pytest.mark.asyncio
async def test_forwarded_for_ignored_from_untrusted_peer(rate_limiting):
    transport = ASGITransport(app=app, client=("198.51.100.7", 1234))
    async with AsyncClient(transport=transport, base_url="http://test") as untrusted:
        for i in range(5):
            assert (await failed_login(untrusted, f"203.0.113.{i}")).status_code == 400
        # Spoofing a new X-Forwarded-For doesn't buy a fresh budget
        assert (await failed_login(untrusted, "203.0.113.99")).status_code == 429


# ── 4. Validation errors never echo or log submitted values ──────────────────


@pytest.mark.asyncio
async def test_validation_error_does_not_echo_or_log_password(client, caplog):
    secret = "Sh0rt!"
    with caplog.at_level(logging.WARNING):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "u1@test.com",
                "username": "user1",
                "password": secret,
            },
        )
    assert response.status_code == 422
    assert secret not in response.text
    assert "body" not in response.json()
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    assert "validation_error" in caplog.text
    assert secret not in caplog.text


# ── 5. User lookups don't expose email addresses ─────────────────────────────


@pytest.mark.asyncio
async def test_user_endpoints_do_not_expose_email(client):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")
    user2 = await register(client, "u2@test.com", "user2")
    headers = auth_header(token1)

    single = await client.get(f"/api/v1/users/?user_id={user2}", headers=headers)
    batch = await client.get(f"/api/v1/users/batch?user_ids={user2}", headers=headers)
    lookup = await client.get("/api/v1/users/lookup?usernames=user2", headers=headers)

    assert single.status_code == batch.status_code == lookup.status_code == 200
    assert set(single.json()) == {"id", "username"}
    assert set(batch.json()[0]) == {"id", "username"}
    assert set(lookup.json()[0]) == {"id", "username"}
    assert "u2@test.com" not in single.text + batch.text + lookup.text


# ── 6a. Creating conversations validates members and is atomic ──────────────


@pytest.mark.asyncio
async def test_create_conversation_unknown_member_creates_nothing(client):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")
    user2 = await register(client, "u2@test.com", "user2")

    response = await create_conversation(client, token1, "group", [user2, 999])
    assert response.status_code == 400
    assert "999" in response.json()["detail"]

    listed = await client.get("/api/v1/conversations/", headers=auth_header(token1))
    assert listed.json() == []


@pytest.mark.asyncio
async def test_create_conversation_dedupes_creator_and_members(client):
    user1, token1 = await register_and_login(client, "u1@test.com", "user1")
    user2 = await register(client, "u2@test.com", "user2")

    response = await create_conversation(client, token1, "group", [user1, user2, user2])
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("extra_members", [0, 2])
async def test_dm_requires_exactly_one_other_member(client, extra_members):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")
    others = [
        await register(client, f"o{i}@test.com", f"other{i}")
        for i in range(extra_members)
    ]

    response = await create_conversation(client, token1, "dm", others)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_dm_is_reused_for_the_same_pair(client):
    user1, token1 = await register_and_login(client, "u1@test.com", "user1")
    user2, token2 = await register_and_login(client, "u2@test.com", "user2")

    first = await create_conversation(client, token1, "dm", [user2])
    again = await create_conversation(client, token1, "dm", [user2])
    reverse = await create_conversation(client, token2, "dm", [user1])

    assert first.status_code == again.status_code == reverse.status_code == 200
    assert first.json()["id"] == again.json()["id"] == reverse.json()["id"]


# ── 6b. Adding members ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_member_unknown_user(client):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")
    conv_id = (await create_conversation(client, token1, "group", [])).json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/members",
        json={"user_id": 999},
        headers=auth_header(token1),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_member_twice_conflicts(client):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")
    user2 = await register(client, "u2@test.com", "user2")
    conv_id = (await create_conversation(client, token1, "group", [user2])).json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/members",
        json={"user_id": user2},
        headers=auth_header(token1),
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_add_member_to_dm_rejected(client):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")
    user2 = await register(client, "u2@test.com", "user2")
    user3 = await register(client, "u3@test.com", "user3")
    conv_id = (await create_conversation(client, token1, "dm", [user2])).json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/members",
        json={"user_id": user3},
        headers=auth_header(token1),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_member_only_by_creator(client):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")
    user2, token2 = await register_and_login(client, "u2@test.com", "user2")
    user3 = await register(client, "u3@test.com", "user3")
    conv_id = (await create_conversation(client, token1, "group", [user2])).json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/members",
        json={"user_id": user3},
        headers=auth_header(token2),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_add_member_conversation_not_found(client):
    _, token1 = await register_and_login(client, "u1@test.com", "user1")

    response = await client.post(
        "/api/v1/conversations/999/members",
        json={"user_id": 1},
        headers=auth_header(token1),
    )
    assert response.status_code == 404


# ── 7. Refresh tokens rotate, can be revoked, and reuse is detected ──────────


@pytest.mark.asyncio
async def test_refresh_rotates_token(client):
    await register(client, "u1@test.com", "user1")
    old = refresh_cookie(await login(client, "u1@test.com"))
    assert old

    response = await post_with_refresh_cookie(client, "/api/v1/auth/refresh", old)
    assert response.status_code == 200
    assert response.json()["access_token"]
    new = refresh_cookie(response)
    assert new and new != old


@pytest.mark.asyncio
async def test_refresh_token_reuse_revokes_all_sessions(client):
    await register(client, "u1@test.com", "user1")
    old = refresh_cookie(await login(client, "u1@test.com"))
    other_session = refresh_cookie(await login(client, "u1@test.com"))
    new = refresh_cookie(
        await post_with_refresh_cookie(client, "/api/v1/auth/refresh", old)
    )

    # Replaying the rotated token is rejected...
    replay = await post_with_refresh_cookie(client, "/api/v1/auth/refresh", old)
    assert replay.status_code == 401

    # ...and ends every session for that user
    for token in (new, other_session):
        response = await post_with_refresh_cookie(client, "/api/v1/auth/refresh", token)
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client):
    await register(client, "u1@test.com", "user1")
    token = refresh_cookie(await login(client, "u1@test.com"))

    logout = await post_with_refresh_cookie(client, "/api/v1/auth/logout", token)
    assert logout.status_code == 200
    assert refresh_cookie(logout) in ("", '""')  # cookie cleared

    response = await post_with_refresh_cookie(client, "/api/v1/auth/refresh", token)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_not_issued_by_server_rejected(client):
    user_id = await register(client, "u1@test.com", "user1")
    # Correctly signed, but never stored (e.g. minted before this deploy)
    forged, _, _ = create_refresh_token(user_id)

    response = await post_with_refresh_cookie(client, "/api/v1/auth/refresh", forged)
    assert response.status_code == 401
