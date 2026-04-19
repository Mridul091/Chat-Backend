// In production (Docker + Nginx), both frontend and API are on the same origin,
// so relative URLs work — /api/v1 routes to FastAPI via Nginx.
// In local dev without Docker, set VITE_API_URL in frontend/.env.local
const API_BASE = import.meta.env.VITE_API_URL ?? '/api/v1';
const WS_BASE = import.meta.env.VITE_WS_URL ?? '';

function getToken() {
  return localStorage.getItem('access_token');
}

function setToken(token) {
  localStorage.setItem('access_token', token);
}

function clearToken() {
  localStorage.removeItem('access_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (res.status === 401) {
    clearToken();
    window.location.reload();
    throw new Error('Unauthorized');
  }

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Something went wrong');
  }
  return data;
}

// Auth
export async function register(username, email, password) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  });
}

export async function login(email, password) {
  const data = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function getMe() {
  return request('/auth/me');
}

export async function logout() {
  try {
    await request('/auth/logout', { method: 'POST' });
  } catch (_) {}
  clearToken();
}

// Conversations
export async function listConversations() {
  return request('/conversations/');
}

export async function createConversation(title, type, memberIds) {
  return request('/conversations/', {
    method: 'POST',
    body: JSON.stringify({ title, type, member_ids: memberIds }),
  });
}

export async function getConversation(id) {
  return request(`/conversations/${id}`);
}

export async function addMember(conversationId, userId) {
  return request(`/conversations/${conversationId}/members`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId }),
  });
}

// Messages
export async function getMessages(conversationId, limit = 50, offset = 0) {
  return request(`/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`);
}

export async function sendMessage(conversationId, content) {
  return request(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

export async function markRead(conversationId) {
  return request(`/conversations/${conversationId}/read`, { method: 'POST' });
}

// WebSocket
export function connectWS(conversationId) {
  const ws = new WebSocket(`${WS_BASE}/ws/${conversationId}`);
  
  ws.addEventListener('open', () => {
    // Send auth message as first frame
    ws.send(JSON.stringify({ token: getToken() }));
  });

  return ws;
}
