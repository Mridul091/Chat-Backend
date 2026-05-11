import { useState, useEffect, useRef } from "react";
import { getMessages, connectWS, markRead } from "../api";

export default function ChatArea({ conversation, currentUser }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [wsStatus, setWsStatus] = useState("disconnected");
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [onlineUsers, setOnlineUsers] = useState(new Set());
  const [seenBy, setSeenBy] = useState(new Set()); // user_ids who have read receipts
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const chatMessagesRef = useRef(null);
  const typingTimeoutRef = useRef({}); // per-user auto-clear timers
  const typingRef = useRef(false); // are WE currently marked as typing?
  const typingSendTimeout = useRef(null); // debounce timer for stop-typing

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch messages and setup WebSocket when conversation changes
  useEffect(() => {
    if (!conversation) return;

    setMessages([]);
    setWsStatus("connecting");
    setSeenBy(new Set());

    // Fetch existing messages
    getMessages(conversation.id, 100, 0)
      .then((msgs) => {
        setMessages(msgs);
        // NOTE: markRead is now called after WS presence_state event
        // to avoid a race condition where the broadcast fires before
        // the WS auth handshake completes.
      })
      .catch(console.error);

    // Connect WebSocket
    const ws = connectWS(conversation.id);
    wsRef.current = ws;

    ws.addEventListener("open", () => {
      // Auth message is sent automatically in connectWS
    });

    ws.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "message") {
          setMessages((prev) => {
            if (prev.some((m) => m.id === data.id)) return prev;
            return [
              ...prev,
              {
                id: data.id,
                sender_id: data.sender_id,
                content: data.content,
                created_at: data.created_at,
                conversation_id: conversation.id,
              },
            ];
          });
        } else if (data.type === "typing_start") {
          if (data.sender_id !== currentUser?.id) {
            setTypingUsers((prev) => new Set(prev).add(data.sender_id));
            // Auto-clear after 3s in case typing_end is never received
            clearTimeout(typingTimeoutRef.current[data.sender_id]);
            typingTimeoutRef.current[data.sender_id] = setTimeout(() => {
              setTypingUsers((prev) => {
                const next = new Set(prev);
                next.delete(data.sender_id);
                return next;
              });
            }, 3000);
          }
        } else if (data.type === "typing_end") {
          clearTimeout(typingTimeoutRef.current[data.sender_id]);
          setTypingUsers((prev) => {
            const next = new Set(prev);
            next.delete(data.sender_id);
            return next;
          });
        } else if (data.type === "user_online") {
          if (data.user_id !== currentUser?.id) {
            setOnlineUsers((prev) => new Set(prev).add(data.user_id));
          }
        } else if (data.type === 'presence_state') {
          // Initialize online users list when connecting
          const others = (data.online_users || []).filter(
            (id) => id !== currentUser?.id,
          );
          setOnlineUsers(new Set(others));
          // Initialize seenBy from users already in this WS room (they've read it)
          const alreadySeen = (data.seen_by || []).filter(
            (id) => currentUser?.id && id !== currentUser.id,
          );
          setSeenBy(new Set(alreadySeen));
          // WS is now fully authenticated and in the room — safe to call markRead
          markRead(conversation.id).catch(() => {});
        } else if (data.type === 'user_offline') {
          setOnlineUsers((prev) => {
            const next = new Set(prev);
            next.delete(data.user_id);
            return next;
          });
          // Also clear seen indicator when user goes offline (logged out)
          setSeenBy((prev) => {
            const next = new Set(prev);
            next.delete(data.user_id);
            return next;
          });
        } else if (data.type === 'error') {
          console.warn('WS error:', data.message);
        } else if (data.type === 'read_receipt') {
          // Guard: ensure currentUser is loaded and we don't add ourselves
          if (currentUser?.id && data.user_id !== currentUser.id) {
            setSeenBy((prev) => new Set(prev).add(data.user_id));
          }
        }
      } catch (err) {
        console.error("WS parse error:", err);
      }
    });

    // Set connected after a short delay (after auth handshake)
    const statusTimer = setTimeout(() => setWsStatus("connected"), 500);

    ws.addEventListener("close", () => {
      setWsStatus("disconnected");
    });

    ws.addEventListener("error", () => {
      setWsStatus("error");
    });

    return () => {
      clearTimeout(statusTimer);
      ws.close();
      wsRef.current = null;
    };
  }, [conversation?.id]);

  const handleSend = (e) => {
    e.preventDefault();
    const content = input.trim();
    if (
      !content ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN
    )
      return;

    // Stop typing indicator when message is sent
    clearTimeout(typingSendTimeout.current);
    if (typingRef.current) {
      typingRef.current = false;
      wsRef.current.send(JSON.stringify({ type: "typing_end" }));
    }

    wsRef.current.send(JSON.stringify({ type: "message", content }));
    setInput("");
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    // Send typing_start only once until we stop typing
    if (!typingRef.current) {
      typingRef.current = true;
      wsRef.current.send(JSON.stringify({ type: "typing_start" }));
    }

    // Reset stop-typing timer on every keystroke
    clearTimeout(typingSendTimeout.current);
    typingSendTimeout.current = setTimeout(() => {
      typingRef.current = false;
      wsRef.current?.send(JSON.stringify({ type: "typing_end" }));
    }, 1500);
  };

  const formatTime = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  if (!conversation) {
    return (
      <div className="chat-area">
        <div className="empty-state">
          <div className="empty-state-icon">💬</div>
          <h3>No chat selected</h3>
          <p>
            Pick a conversation from the sidebar or create a new one to start
            chatting.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-area">
      <div className="chat-header">
        <div className="chat-header-info">
          <div
            className="conversation-avatar"
            style={{ width: 36, height: 36, fontSize: 14 }}
          >
            {(conversation.title || `C`).charAt(0).toUpperCase()}
          </div>
          <div>
            <h3>{conversation.title || `Conversation #${conversation.id}`}</h3>
            <span className="chat-type">{conversation.type}</span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background:
                wsStatus === "connected"
                  ? "var(--success)"
                  : wsStatus === "connecting"
                    ? "var(--warning)"
                    : "var(--error)",
            }}
          />
          <span
            style={{
              fontSize: 11,
              color: "var(--text-muted)",
              textTransform: "capitalize",
            }}
          >
            {wsStatus}
          </span>
        </div>
      </div>

      <div className="chat-messages" ref={chatMessagesRef}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <p style={{ fontSize: "13px" }}>
              No messages yet. Say something! 👋
            </p>
          </div>
        ) : (
          (() => {
            // Find index of last message sent by current user (for Seen indicator)
            const lastSentIndex = messages.reduce(
              (last, msg, idx) => (msg.sender_id === currentUser?.id ? idx : last),
              -1
            );
            return messages.map((msg, index) => {
            const isSent = msg.sender_id === currentUser?.id;
            return (
              <div
                key={msg.id}
                className={`message ${isSent ? "sent" : "received"}`}
              >
                {!isSent && (
                  <div
                    className="message-sender"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    User #{msg.sender_id}
                    {onlineUsers.has(msg.sender_id) && (
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          backgroundColor: "var(--success)",
                        }}
                        title="Online"
                      />
                    )}
                  </div>
                )}
                <div>{msg.content}</div>
                <div className="message-time">{formatTime(msg.created_at)}</div>
                {/* Seen indicator only under the last sent message */}
                {isSent && index === lastSentIndex && seenBy.size > 0 && (
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'right', marginTop: 2 }}>
                    Seen ✓✓
                  </div>
                )}
              </div>
            );
          })
          })()
        )}
        <div ref={messagesEndRef} />
      </div>

      {typingUsers.size > 0 && (
        <div
          style={{
            padding: "4px 20px 2px",
            fontSize: 12,
            color: "var(--text-muted)",
            fontStyle: "italic",
            minHeight: 20,
          }}
        >
          {typingUsers.size === 1
            ? `User #${[...typingUsers][0]} is typing...`
            : `${typingUsers.size} people are typing...`}
        </div>
      )}

      <div className="chat-input-area">
        <form className="chat-input-wrapper" onSubmit={handleSend}>
          <input
            type="text"
            placeholder="Type a message..."
            value={input}
            onChange={handleInputChange}
            maxLength={4000}
            autoFocus
          />
          <button type="submit" className="btn-send" disabled={!input.trim()}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
