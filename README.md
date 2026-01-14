# AI Dialogue Hub

A monorepo containing Telegram bots and a web dashboard for AI consulting and message logging.

## Services

| Service | Description | Tech Stack |
|---------|-------------|------------|
| **Facto** | AI consultant bot with forum topic workflows | Python, OpenAI |
| **Logta** | Message logger that archives to MongoDB | Python, MongoDB |
| **Dashboard** | Web UI for browsing logged messages | Next.js, Meilisearch |

## Project Structure

```
ai-dialogue-hub/
├── compose.yml              # docker orchestration
├── compose.prod.yml         # production overrides
├── requirements.txt         # combined deps for local dev
└── src/
    ├── facto/               # ai consultant bot
    │   ├── main.py
    │   ├── config.py
    │   ├── bot/
    │   ├── core/
    │   └── services/
    ├── logta/               # message logger bot
    │   ├── main.py
    │   ├── config.py
    │   ├── handlers.py
    │   └── services/
    └── dashboard/           # next.js web interface
        ├── app/
        ├── components/
        └── server/
```

## Quick Start

### 1. Create Telegram Bots

Create bots via [@BotFather](https://t.me/BotFather):

For both bots, disable Privacy Mode:
```
/mybots → Select bot → Bot Settings → Group Privacy → Turn off
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```ini
# facto bot
FACTO_TOKEN=your_facto_bot_token
OPENAI_API_KEY=your_openai_api_key

# logta bot
LOGTA_TOKEN=your_logta_bot_token
MONGODB_URI=mongodb://mongodb:27017
OWNER_ID=your_telegram_user_id
```

### 3. Run with Docker

```bash
# all services
docker compose up -d

# individual services
docker compose up -d facto
docker compose up -d logta mongodb
docker compose up -d dashboard
```

### 4. Local Development

```bash
pip install -r requirements.txt

# run facto
python -m facto.main

# run logta (requires mongodb)
python -m logta.main
```

---

## Facto Bot

AI consultant that creates forum topics for structured conversations.

### Setup

1. Add bot to a Telegram group with Topics enabled
2. Promote bot to admin with **Manage Topics** and **Delete Messages**

### Commands

| Command | Description |
|---------|-------------|
| `/code` | Switch to software engineering mode |
| `/code <question>` | Start a code topic with your question |
| `/general` | Switch to general consultant mode |
| `/general <question>` | Start a general topic with your question |
| `/delete` | Delete current topic (use inside a topic) |

### Workflow

1. User posts a message in the General topic
2. Bot creates a new forum topic
3. Bot asks clarifying questions one at a time
4. Bot generates solution in markdown
5. Bot cleans up Q&A history and closes the topic

---

## Logta Bot

Message archiver that logs all messages to MongoDB.

### Setup

1. Add bot to groups you want to log
2. Bot automatically starts logging messages

### Commands

| Command | Description |
|---------|-------------|
| `/stats` | Show message/event counts (owner only) |
| `/topic <msg>` | Create forum topic with AI-generated title |
| `/history` | Get conversation history for current topic |

### MongoDB Collections

| Collection | Description |
|------------|-------------|
| `messages` | User content (text, photos, videos, etc.) |
| `events` | System events (joins, leaves, migrations) |
| `activated_chats` | Tracked chat activation state |

---

## Dashboard

Next.js web interface for browsing and searching logged messages.

### Features

- Browse messages by group/chat
- Full-text search via Meilisearch
- Real-time updates via WebSocket
- View edit history for modified messages

---

## Environment Variables

### Facto Bot

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FACTO_TOKEN` | Yes | - | Bot token from BotFather |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | Custom LLM endpoint |
| `MODEL_NAME` | No | `gpt-4o` | Model name |

### Logta Bot

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOGTA_TOKEN` | Yes | - | Bot token from BotFather |
| `MONGODB_URI` | Yes | - | MongoDB connection string |
| `OWNER_ID` | Yes | - | Your Telegram user ID |
| `MONGODB_DATABASE` | No | `telegram_logs` | Database name |
| `OPENAI_API_KEY` | No | - | For AI topic title generation |
| `LOGTA_MODEL_NAME` | No | `gpt-4o-mini` | Model for title generation |

### Dashboard

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGODB_URI` | Yes | - | MongoDB connection string |
| `MEILISEARCH_URL` | Yes | - | Meilisearch endpoint |
| `MEILISEARCH_API_KEY` | No | - | Meilisearch API key |

## License

MIT
