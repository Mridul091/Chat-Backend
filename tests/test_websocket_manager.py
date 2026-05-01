import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio
import time

from app.websocket.manager import ConnectionManager


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_ws():
    """Return a mock WebSocket that records sent JSON."""
    ws = MagicMock()
    ws.send_json = AsyncMock()
    return ws


# ── connect / disconnect ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connect_adds_to_rooms_and_active_users():
    mgr = ConnectionManager()
    ws = make_ws()
    await mgr.connect(ws, conversation_id=1, user_id=10)

    assert ws in mgr.rooms[1]
    assert ws in mgr.active_users[10]


@pytest.mark.asyncio
async def test_connect_multiple_ws_same_room():
    mgr = ConnectionManager()
    ws1, ws2 = make_ws(), make_ws()
    await mgr.connect(ws1, conversation_id=1, user_id=10)
    await mgr.connect(ws2, conversation_id=1, user_id=20)

    assert ws1 in mgr.rooms[1]
    assert ws2 in mgr.rooms[1]


@pytest.mark.asyncio
async def test_connect_same_user_multiple_tabs():
    mgr = ConnectionManager()
    ws1, ws2 = make_ws(), make_ws()
    await mgr.connect(ws1, conversation_id=1, user_id=10)
    await mgr.connect(ws2, conversation_id=1, user_id=10)

    assert len(mgr.active_users[10]) == 2


def test_disconnect_removes_ws_from_room():
    mgr = ConnectionManager()
    ws = make_ws()
    mgr.rooms[1] = {ws}
    mgr.active_users[10] = {ws}
    mgr.disconnect(ws, conversation_id=1, user_id=10)

    assert ws not in mgr.rooms.get(1, set())


def test_disconnect_removes_user_when_last_ws():
    mgr = ConnectionManager()
    ws = make_ws()
    mgr.rooms[1] = {ws}
    mgr.active_users[10] = {ws}
    mgr.disconnect(ws, conversation_id=1, user_id=10)

    assert 10 not in mgr.active_users


def test_disconnect_keeps_user_when_other_tabs_open():
    mgr = ConnectionManager()
    ws1, ws2 = make_ws(), make_ws()
    mgr.rooms[1] = {ws1, ws2}
    mgr.active_users[10] = {ws1, ws2}
    mgr.disconnect(ws1, conversation_id=1, user_id=10)

    assert 10 in mgr.active_users
    assert ws2 in mgr.active_users[10]


def test_disconnect_unknown_ws_does_not_raise():
    mgr = ConnectionManager()
    ws = make_ws()
    # Should not raise even when the ws was never added
    mgr.disconnect(ws, conversation_id=99, user_id=99)


# ── is_user_online ───────────────────────────────────────────────────────────

def test_is_user_online_true_when_connected():
    mgr = ConnectionManager()
    ws = make_ws()
    mgr.active_users[10] = {ws}
    assert mgr.is_user_online(10) is True


def test_is_user_online_false_when_not_connected():
    mgr = ConnectionManager()
    assert mgr.is_user_online(10) is False


def test_is_user_online_false_after_disconnect():
    mgr = ConnectionManager()
    ws = make_ws()
    mgr.rooms[1] = {ws}
    mgr.active_users[10] = {ws}
    mgr.disconnect(ws, conversation_id=1, user_id=10)
    assert mgr.is_user_online(10) is False


# ── broadcast ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_broadcast_sends_to_all_room_members():
    mgr = ConnectionManager()
    ws1, ws2 = make_ws(), make_ws()
    mgr.rooms[1] = {ws1, ws2}

    await mgr.broadcast(1, {"type": "message", "content": "hello"})

    ws1.send_json.assert_called_once_with({"type": "message", "content": "hello"})
    ws2.send_json.assert_called_once_with({"type": "message", "content": "hello"})


@pytest.mark.asyncio
async def test_broadcast_empty_room_does_not_raise():
    mgr = ConnectionManager()
    # No exception expected for a room with no members
    await mgr.broadcast(999, {"type": "message", "content": "hello"})


@pytest.mark.asyncio
async def test_broadcast_does_not_send_to_other_rooms():
    mgr = ConnectionManager()
    ws1, ws2 = make_ws(), make_ws()
    mgr.rooms[1] = {ws1}
    mgr.rooms[2] = {ws2}

    await mgr.broadcast(1, {"type": "message", "content": "room1"})

    ws1.send_json.assert_called_once()
    ws2.send_json.assert_not_called()


# ── send_personal_message ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_personal_message_to_online_user():
    mgr = ConnectionManager()
    ws = make_ws()
    mgr.active_users[10] = {ws}

    await mgr.send_personal_message(10, {"type": "dm", "content": "hi"})
    ws.send_json.assert_called_once_with({"type": "dm", "content": "hi"})


@pytest.mark.asyncio
async def test_send_personal_message_offline_user_does_not_raise():
    mgr = ConnectionManager()
    # Should not raise when user is offline
    await mgr.send_personal_message(999, {"type": "dm", "content": "hi"})


@pytest.mark.asyncio
async def test_send_personal_message_all_tabs_receive():
    mgr = ConnectionManager()
    ws1, ws2 = make_ws(), make_ws()
    mgr.active_users[10] = {ws1, ws2}

    await mgr.send_personal_message(10, {"type": "dm", "content": "hi"})
    ws1.send_json.assert_called_once()
    ws2.send_json.assert_called_once()


# ── check_rate_limit ─────────────────────────────────────────────────────────

def test_check_rate_limit_allows_under_limit():
    mgr = ConnectionManager()
    for _ in range(4):
        assert mgr.check_rate_limit(1, max_messages=5, time_window=1.0) is True


def test_check_rate_limit_blocks_at_limit():
    mgr = ConnectionManager()
    for _ in range(5):
        mgr.check_rate_limit(1, max_messages=5, time_window=1.0)
    assert mgr.check_rate_limit(1, max_messages=5, time_window=1.0) is False


def test_check_rate_limit_resets_after_window(monkeypatch):
    mgr = ConnectionManager()
    fake_time = [0.0]

    def mock_time():
        return fake_time[0]

    import app.websocket.manager as mgr_module
    monkeypatch.setattr(mgr_module.time, "time", mock_time)

    # Fill up the window at t=0
    for _ in range(5):
        mgr.check_rate_limit(1, max_messages=5, time_window=1.0)

    # Advance time past the window
    fake_time[0] = 2.0
    # Now the old timestamps are expired; new messages should be allowed
    assert mgr.check_rate_limit(1, max_messages=5, time_window=1.0) is True


def test_check_rate_limit_independent_per_user():
    mgr = ConnectionManager()
    for _ in range(5):
        mgr.check_rate_limit(1, max_messages=5, time_window=1.0)
    # User 2 should still be under the limit
    assert mgr.check_rate_limit(2, max_messages=5, time_window=1.0) is True
