import { useState } from 'react';
import { createConversation } from '../api';
import CreateConversationModal from './CreateConversationModal';

export default function Sidebar({
  user,
  conversations,
  activeConversation,
  onSelectConversation,
  onConversationCreated,
  onLogout,
}) {
  const [showModal, setShowModal] = useState(false);

  const getInitials = (name) => {
    if (!name) return '?';
    return name
      .split(' ')
      .map((w) => w[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getConversationName = (conv) => {
    return conv.title || `Conversation #${conv.id}`;
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>💬 Chats</h2>
        <div className="sidebar-header-actions">
          <button
            className="btn-icon"
            onClick={() => setShowModal(true)}
            title="New conversation"
          >
            ＋
          </button>
        </div>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div style={{ padding: '24px 16px', textAlign: 'center' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
              No conversations yet.
              <br />
              Click + to start one.
            </p>
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                activeConversation?.id === conv.id ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv)}
            >
              <div className="conversation-avatar">
                {getInitials(getConversationName(conv))}
              </div>
              <div className="conversation-info">
                <div className="conversation-name">
                  {getConversationName(conv)}
                </div>
                <div className="conversation-preview">
                  {conv.type === 'dm' ? 'Direct message' : 'Group chat'}
                </div>
              </div>
              <div className="conversation-time">
                {new Date(conv.created_at).toLocaleDateString()}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="sidebar-user">
        <div className="user-avatar">{getInitials(user?.username)}</div>
        <div className="user-info">
          <div className="user-name">{user?.username}</div>
          <div className="user-email">{user?.email}</div>
        </div>
        <button className="btn-logout" onClick={onLogout}>
          Logout
        </button>
      </div>

      {showModal && (
        <CreateConversationModal
          onClose={() => setShowModal(false)}
          onCreate={onConversationCreated}
        />
      )}
    </div>
  );
}
