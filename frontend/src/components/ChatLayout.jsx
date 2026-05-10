import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { listConversations } from '../api';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';

export default function ChatLayout() {
  const { user, logout } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);

  const fetchConversations = async () => {
    try {
      const data = await listConversations();
      setConversations(data);
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
    }
  };

  useEffect(() => {
    fetchConversations();

    // Poll every 5s so unread badges stay fresh even when not in a conversation
    const interval = setInterval(fetchConversations, 5000);

    // Also refresh when the user tabs back into the window
    const onFocus = () => fetchConversations();
    window.addEventListener('focus', onFocus);

    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', onFocus);
    };
  }, []);

  const handleConversationCreated = (newConv) => {
    setConversations((prev) => [newConv, ...prev]);
    setActiveConversation(newConv);
  };

  const handleSelectConversation = (conv) => {
    setActiveConversation(conv);
    // Clear unread badge immediately (optimistic update)
    setConversations((prev) =>
      prev.map((c) => (c.id === conv.id ? { ...c, unread_count: 0 } : c))
    );
  };

  return (
    <div className="chat-app">
      <Sidebar
        user={user}
        conversations={conversations}
        activeConversation={activeConversation}
        onSelectConversation={handleSelectConversation}
        onConversationCreated={handleConversationCreated}
        onLogout={logout}
      />
      <ChatArea
        conversation={activeConversation}
        currentUser={user}
      />
    </div>
  );
}
