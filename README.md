# Chat-Backend

A full-stack real-time chat application built with **FastAPI** and **React**. It supports JWT-based authentication, persistent conversations, and live messaging via WebSockets.

---

## Features

- **Authentication** – Register, login, and logout with JWT access tokens and HttpOnly refresh-token cookies
- **Conversations** – Create group or direct conversations, list them, and manage members
- **Messaging** – Send and retrieve paginated messages; poll for new messages with a `since` timestamp
- **Real-time** – WebSocket endpoint per conversation with:
  - Live message delivery
  - Typing indicators (`typing_start` / `typing_end`)
  - Presence events (`user_online` / `user_offline` / `presence_state`)
  - Per-connection rate limiting (5 messages / second)
- **Rate limiting** – SlowAPI guards every REST endpoint
- **Structured logging** – Request-scoped logging via structlog
- **Database migrations** – Alembic manages the PostgreSQL schema

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.129, Python 3.12 |
| Database | PostgreSQL 16, SQLAlchemy 2 (async), asyncpg |
| Migrations | Alembic |
| Auth | python-jose (JWT), bcrypt |
| Cache / Pub-sub | Redis 7 |
| Frontend | React 19, Vite 8 |
| Reverse proxy | Nginx 1.25 |
| Containerisation | Docker, Docker Compose |
| Testing | pytest, pytest-asyncio, httpx, aiosqlite |
| Linting | Ruff |

---

## Project Structure

```
.
├── app/                    # FastAPI application
│   ├── api/v1/             # REST route handlers (auth, conversations, health)
│   ├── core/               # Config, DB, dependencies, error handling, logging
│   ├── models/             # SQLAlchemy ORM models
│   ├── repositories/       # Database access layer
│   ├── schemas/            # Pydantic request / response schemas
│   ├── services/           # Business logic
│   └── websocket/          # WebSocket router, auth, connection manager
├── alembic/                # Database migration scripts
├── frontend/               # React + Vite frontend
├── nginx/                  # Nginx reverse-proxy config
├── tests/                  # pytest test suite
├── Dockerfile              # Multi-stage backend image
├── docker-compose.yml      # Full-stack local setup
├── docker-compose.prod.yml # Production compose override
└── pyproject.toml          # Python dependencies (Poetry)
```

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- (Optional, for local dev) Python 3.12+, [Poetry](https://python-poetry.org/), Node.js 20+

### 1. Clone the repository

```bash
git clone https://github.com/Mridul091/Chat-Backend.git
cd Chat-Backend
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```env
# Application
DATABASE_URL=postgresql+asyncpg://<user>:<password>@postgres:5432/<db>
SECRET_KEY=<generate-a-strong-random-secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Postgres credentials (used by Docker Compose)
POSTGRES_USER=<your-db-user>
POSTGRES_PASSWORD=<your-db-password>
POSTGRES_DB=<your-db-name>
```

Generate a secure secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start with Docker Compose

```bash
docker compose up --build
```

The application is served at **http://localhost** (port 80) through Nginx.

---

## Local Development (without Docker)

### Backend

```bash
# Install dependencies
poetry install

# Run database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # starts Vite on http://localhost:5173
```

---

## Running Tests

```bash
poetry run pytest
```

The test suite uses an in-memory SQLite database (via aiosqlite) so no running PostgreSQL instance is needed.

---

## API Reference

All REST endpoints are prefixed with `/api/v1`.  
Interactive docs are available at **http://localhost:8000/docs** when the backend is running.

### Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a new account |
| `POST` | `/auth/login` | Login and receive an access token |
| `POST` | `/auth/refresh` | Rotate tokens using the refresh-token cookie |
| `GET` | `/auth/me` | Get the current authenticated user |
| `POST` | `/auth/logout` | Clear the refresh-token cookie |

### Conversations

| Method | Path | Description |
|---|---|---|
| `POST` | `/conversations/` | Create a new conversation |
| `GET` | `/conversations/` | List conversations for the current user |
| `GET` | `/conversations/{id}` | Get a single conversation |
| `POST` | `/conversations/{id}/members` | Add a member to a conversation |

### Messages

| Method | Path | Description |
|---|---|---|
| `POST` | `/conversations/{id}/messages` | Send a message |
| `GET` | `/conversations/{id}/messages` | Get paginated messages (`limit`, `offset`, `since`) |
| `POST` | `/conversations/{id}/read` | Mark conversation as read |

### WebSocket

Connect to `ws://<host>/ws/{conversation_id}`.

After connecting, send an auth frame as the first message:

```json
{ "token": "<access_token>" }
```

#### Outgoing message types (client → server)

| Type | Payload | Description |
|---|---|---|
| *(default)* | `{ "content": "Hello!" }` | Send a chat message |
| `typing_start` | `{ "type": "typing_start" }` | Notify others that you are typing |
| `typing_end` | `{ "type": "typing_end" }` | Notify others that you stopped typing |

#### Incoming event types (server → client)

| Type | Description |
|---|---|
| `message` | A new chat message |
| `typing_start` | A user started typing |
| `typing_end` | A user stopped typing |
| `user_online` | A user joined the conversation |
| `user_offline` | A user left the conversation |
| `presence_state` | Full list of currently online users (sent on connect) |
| `error` | An error occurred (e.g. rate limit exceeded) |

---

## Linting

```bash
poetry run ruff check .
poetry run ruff format .
```

---

## License

This project is open source. See [LICENSE](LICENSE) for details.
