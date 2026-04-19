import { useState, useEffect, useRef } from 'react';
import { getMessages, connectWS, markRead } from '../api';

export default function ChatArea({ conversation, currentUser }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [wsStatus, setWsStatus] = useState('disconnected');
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const chatMessagesRef = useRef(null);

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch messages and setup WebSocket when conversation changes
  useEffect(() => {
    if (!conversation) return;

    setMessages([]);
    setWsStatus('connecting');

    // Fetch existing messages
    getMessages(conversation.id, 100, 0)
      .then((msgs) => {
        setMessages(msgs);
        markRead(conversation.id).catch(() => {});
      })
      .catch(console.error);

    // Connect WebSocket
    const ws = connectWS(conversation.id);
    wsRef.current = ws;

    ws.addEventListener('open', () => {
      // Auth message is sent automatically in connectWS
    });

    ws.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
          setMessages((prev) => {
            // Deduplicate by checking if we already have this message
            if (prev.some((m) => m.id === data.id)) return prev;
            return [...prev, {
              id: data.id,
              sender_id: data.sender_id,
              content: data.content,
              created_at: data.created_at,
              conversation_id: conversation.id,
            }];
          });
        } else if (data.type === 'error') {
          console.warn('WS error:', data.message);
        }
      } catch (err) {
        console.error('WS parse error:', err);
      }
    });

    // Set connected after a short delay (after auth handshake)
    const statusTimer = setTimeout(() => setWsStatus('connected'), 500);

    ws.addEventListener('close', () => {
      setWsStatus('disconnected');
    });

    ws.addEventListener('error', () => {
      setWsStatus('error');
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
    if (!content || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({ content }));
    setInput('');
  };

  const formatTime = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (!conversation) {
    return (
      <div className="chat-area">
        <div className="empty-state">
          <div className="empty-state-icon">💬</div>
          <h3>No chat selected</h3>
          <p>Pick a conversation from the sidebar or create a new one to start chatting.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-area">
      <div className="chat-header">
        <div className="chat-header-info">
          <div className="conversation-avatar" style={{ width: 36, height: 36, fontSize: 14 }}>
            {(conversation.title || `C`).charAt(0).toUpperCase()}
          </div>
          <div>
            <h3>{conversation.title || `Conversation #${conversation.id}`}</h3>
            <span className="chat-type">{conversation.type}</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background:
                wsStatus === 'connected'
                  ? 'var(--success)'
                  : wsStatus === 'connecting'
                  ? 'var(--warning)'
                  : 'var(--error)',
            }}
          />
          <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
            {wsStatus}
          </span>
        </div>
      </div>

      <div className="chat-messages" ref={chatMessagesRef}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <p style={{ fontSize: '13px' }}>No messages yet. Say something! 👋</p>
          </div>
        ) : (
          messages.map((msg) => {
            const isSent = msg.sender_id === currentUser?.id;
            return (
              <div
                key={msg.id}
                className={`message ${isSent ? 'sent' : 'received'}`}
              >
                {!isSent && (
                  <div className="message-sender">User #{msg.sender_id}</div>
                )}
                <div>{msg.content}</div>
                <div className="message-time">{formatTime(msg.created_at)}</div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <form className="chat-input-wrapper" onSubmit={handleSend}>
          <input
            type="text"
            placeholder="Type a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={4000}
            autoFocus
          />
          <button type="submit" className="btn-send" disabled={!input.trim()}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
