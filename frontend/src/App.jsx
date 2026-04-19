import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './components/AuthPage';
import ChatLayout from './components/ChatLayout';

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" style={{ width: 32, height: 32 }} />
      </div>
    );
  }

  return user ? <ChatLayout /> : <AuthPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
