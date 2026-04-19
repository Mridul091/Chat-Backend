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
  }, []);

  const handleConversationCreated = (newConv) => {
    setConversations((prev) => [newConv, ...prev]);
    setActiveConversation(newConv);
  };

  return (
    <div className="chat-app">
      <Sidebar
        user={user}
        conversations={conversations}
        activeConversation={activeConversation}
        onSelectConversation={setActiveConversation}
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
