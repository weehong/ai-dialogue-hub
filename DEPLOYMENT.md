# Facto Bot Suite - Deployment Guide

Complete deployment guide for the Facto bot suite: **Facto** (AI Consultant Bot) and **Logta** (Message Logger Bot).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Telegram Bot Setup](#2-telegram-bot-setup)
3. [Environment Configuration](#3-environment-configuration)
4. [Deployment Options](#4-deployment-options)
   - [Docker Compose (Recommended)](#option-a-docker-compose-recommended)
   - [Docker Run](#option-b-docker-run)
   - [Local Development](#option-c-local-development)
5. [Post-Deployment Setup](#5-post-deployment-setup)
6. [Verification](#6-verification)
7. [Maintenance](#7-maintenance)
8. [Troubleshooting](#8-troubleshooting)
9. [Remote Access with Tailscale](#9-remote-access-with-tailscale)

---

## 1. Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | v2.0+ | Multi-container orchestration |
| Git | Any | Clone repository |

### Required Accounts

- **Telegram Account**: To create bots via @BotFather
- **OpenAI Account**: For AI features (or compatible API like DeepSeek)

### Get Your Telegram User ID

You need your numeric Telegram user ID for the Logta bot owner configuration:

1. Open Telegram and search for `@userinfobot`
2. Start the bot and send any message
3. Copy your numeric ID (e.g., `123456789`)

---

## 2. Telegram Bot Setup

You need to create **two separate bots** in Telegram.

### Step 2.1: Create Facto Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Enter a name: `Facto AI Consultant` (or your choice)
4. Enter a username: `facto_ai_bot` (must end with `bot`)
5. **Save the token** - you'll need it for `FACTO_TOKEN`

### Step 2.2: Create Logta Bot

1. In @BotFather, send `/newbot` again
2. Enter a name: `Logta Message Logger` (or your choice)
3. Enter a username: `logta_logger_bot` (must end with `bot`)
4. **Save the token** - you'll need it for `LOGTA_TOKEN`

### Step 2.3: Disable Group Privacy (CRITICAL)

> **Both bots require Group Privacy to be DISABLED to receive messages in groups.**

For **each bot**, do the following:

1. In @BotFather, send `/mybots`
2. Select the bot
3. Click **Bot Settings**
4. Click **Group Privacy**
5. Click **Turn off**

Verify it shows: `Privacy mode is disabled for YourBot`

### Step 2.4: Configure Facto Bot Permissions

The Facto bot needs admin permissions to manage forum topics:

1. Add the Facto bot to your Telegram group
2. Go to group settings → Administrators
3. Add the bot as administrator with these permissions:
   - **Manage Topics** (required to create/close topics)
   - **Delete Messages** (required to clean conversation history)

---

## 3. Environment Configuration

### Step 3.1: Create Environment File

```bash
cp .env.example .env
```

### Step 3.2: Configure Variables

Edit `.env` with your values:

```bash
# ===========================================
# Facto Bot (AI Consultant)
# ===========================================

# Telegram Bot Token (from @BotFather - Step 2.1)
FACTO_TOKEN=your_facto_bot_token_here

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Use alternative LLM provider (e.g., DeepSeek)
# OPENAI_BASE_URL=https://api.deepseek.com
# MODEL_NAME=deepseek-chat

# Default: OpenAI GPT-4o
# OPENAI_BASE_URL=https://api.openai.com/v1
# MODEL_NAME=gpt-4o

# ===========================================
# Logta Bot (Message Logger)
# ===========================================

# Telegram Bot Token (from @BotFather - Step 2.2)
LOGTA_TOKEN=your_logta_bot_token_here

# MongoDB Connection URI
MONGODB_URI=mongodb://mongodb:27017

# Database name (optional, default: telegram_logs)
MONGODB_DATABASE=telegram_logs

# Your Telegram user ID (from @userinfobot)
OWNER_ID=your_telegram_user_id
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FACTO_TOKEN` | Yes | - | Facto bot token from @BotFather |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | LLM API endpoint |
| `MODEL_NAME` | No | `gpt-4o` | LLM model to use |
| `LOGTA_TOKEN` | Yes | - | Logta bot token from @BotFather |
| `MONGODB_URI` | Yes | - | MongoDB connection string |
| `MONGODB_DATABASE` | No | `telegram_logs` | Database name |
| `OWNER_ID` | Yes | - | Your Telegram user ID |

---

## 4. Deployment Options

### Option A: Docker Compose (Recommended)

The simplest way to deploy all services together.

#### Deploy

```bash
# Clone the repository
git clone <repository-url>
cd facto

# Create and configure .env file (see Step 3)
cp .env.example .env
nano .env  # Edit with your values

# Build and start all services
docker compose up -d --build

# View logs
docker compose logs -f
```

#### Services Started

| Service | Description | Port |
|---------|-------------|------|
| `facto` | AI Consultant Bot | - |
| `logta` | Message Logger Bot | - |
| `mongodb` | Database | 27017 (internal) |

#### Manage Services

```bash
# Stop all services
docker compose down

# Restart a specific service
docker compose restart facto

# View service status
docker compose ps

# View logs for specific service
docker compose logs -f logta

# Rebuild after code changes
docker compose up -d --build
```

---

### Option B: Docker Run

Deploy individual containers without Docker Compose.

#### Step 1: Create Docker Network

```bash
docker network create facto-network
```

#### Step 2: Start MongoDB

```bash
docker run -d \
  --name facto-mongodb \
  --network facto-network \
  --restart always \
  -v facto_mongo_data:/data/db \
  mongo:7
```

#### Step 3: Build and Run Facto Bot

```bash
# Build
docker build -t facto-bot ./src/facto

# Run
docker run -d \
  --name facto-facto \
  --network facto-network \
  --restart always \
  --env-file .env \
  facto-bot
```

#### Step 4: Build and Run Logta Bot

```bash
# Build
docker build -t logta-bot ./src/logta

# Run
docker run -d \
  --name facto-logta \
  --network facto-network \
  --restart always \
  --env-file .env \
  logta-bot
```

---

### Option C: Local Development

Run the bots locally without Docker.

#### Step 1: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Start MongoDB

Either use Docker:
```bash
docker run -d -p 27017:27017 --name mongodb mongo:7
```

Or install MongoDB locally and start the service.

Update `.env`:
```bash
MONGODB_URI=mongodb://localhost:27017
```

#### Step 3: Run Bots

In separate terminals:

```bash
# Terminal 1: Facto Bot
source .venv/bin/activate
cd src
python -m facto.main
```

```bash
# Terminal 2: Logta Bot
source .venv/bin/activate
cd src
python -m logta.main
```

---

## 5. Post-Deployment Setup

### Step 5.1: Add Bots to Groups

1. **Facto Bot**: Add to a group with **Topics enabled**
   - The group must be a "Forum" type (Topics feature enabled in group settings)
   - Promote bot to admin with Manage Topics and Delete Messages permissions

2. **Logta Bot**: Add to any group you want to log

### Step 5.2: Test Facto Bot

1. Go to the General topic in your forum group
2. Post a message (e.g., "Help me optimize my database queries")
3. The bot should:
   - Create a new topic with your message as the title
   - Start asking clarifying questions
   - Generate a solution after the Q&A

Commands available:
- `/code <question>` - Switch to code/software engineering mode
- `/general <question>` - Switch to general consulting mode
- `/delete` - Delete the current topic (use inside a topic)

---

## 6. Verification

### Check Service Status

```bash
docker compose ps
```

Expected output:
```
NAME              IMAGE         STATUS
facto-facto-1     facto-facto   Up X minutes
facto-logta-1     facto-logta   Up X minutes
facto-mongodb-1   mongo:7       Up X minutes (healthy)
```

### Check Logs

```bash
# All services
docker compose logs --tail=50

# Specific service
docker compose logs -f facto
docker compose logs -f logta
```

### Expected Log Output

**Facto Bot:**
```
INFO - Configuration loaded successfully
INFO - Facto Bot starting...
INFO - Commands: /code, /general, /delete
```

**Logta Bot:**
```
INFO - Configuration loaded successfully
INFO - Loaded X activated chats
INFO - MongoDB indexes created for messages and events collections
INFO - Connected to MongoDB: telegram_logs (messages + events collections)
INFO - Message Logger Bot starting...
INFO - REMINDER: Make sure 'Group Privacy' is DISABLED in @BotFather settings!
INFO - Application started
```

### Test MongoDB Connection

```bash
docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

Expected: `{ ok: 1 }`

---

## 7. Maintenance

### Backup MongoDB Data

```bash
# Create backup
docker compose exec mongodb mongodump --out=/data/backup

# Copy backup to host
docker cp facto-mongodb-1:/data/backup ./backup
```

### Restore MongoDB Data

```bash
# Copy backup to container
docker cp ./backup facto-mongodb-1:/data/backup

# Restore
docker compose exec mongodb mongorestore /data/backup
```

### Update Deployment

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker compose up -d --build
```

### View MongoDB Data

```bash
# Connect to MongoDB shell
docker compose exec mongodb mongosh

# In mongosh:
use telegram_logs
db.messages.countDocuments()
db.activated_chats.find()
db.messages.find().sort({date: -1}).limit(5)
```

### Clean Up

```bash
# Stop and remove containers
docker compose down

# Remove volumes (WARNING: deletes all data)
docker compose down -v

# Remove unused images
docker image prune
```

---

## 8. Troubleshooting

### Bot Not Receiving Messages

**Symptom**: Bot is online but doesn't respond to messages in groups.

**Solution**:
1. Verify Group Privacy is **disabled** in @BotFather
2. Check bot is a member of the group

### Configuration Error on Startup

**Symptom**: Container restarts repeatedly with config error.

**Log Example**:
```
ERROR - Configuration error: FACTO_TOKEN environment variable is required
```

**Solution**:
1. Check `.env` file exists and has correct values
2. Verify no typos in variable names
3. Ensure `.env` file is in the project root

### MongoDB Connection Failed

**Symptom**: Logta bot fails to connect to MongoDB.

**Log Example**:
```
ERROR - Failed to connect to MongoDB: ...
```

**Solution**:
1. Check MongoDB container is running: `docker compose ps`
2. Verify `MONGODB_URI` matches the container name (default: `mongodb://mongodb:27017`)
3. Check MongoDB health: `docker compose logs mongodb`

### Telegram Conflict Error

**Symptom**: Bot shows conflict error about multiple instances.

**Log Example**:
```
telegram.error.Conflict: terminated by other getUpdates request
```

**Solution**:
1. Only one instance of each bot can run at a time
2. Stop any other instances: `docker compose down`
3. Check for orphan containers: `docker ps -a | grep facto`
4. Remove orphans: `docker compose down --remove-orphans`

### Facto Bot Not Creating Topics

**Symptom**: Messages in General topic don't create new topics.

**Solution**:
1. Verify group has Topics enabled (Forum type)
2. Check bot has admin permissions:
   - Manage Topics
   - Delete Messages
3. Ensure posting in the **General** topic (not a sub-topic)

### Permission Denied Errors

**Symptom**: Bot can't delete messages or manage topics.

**Solution**:
1. Re-check bot admin permissions in group settings
2. Remove and re-add bot as admin
3. Verify permissions: Manage Topics, Delete Messages

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                          │
├─────────────────┬─────────────────┬─────────────────────────┤
│                 │                 │                         │
│   facto         │   logta         │   mongodb               │
│   (AI Bot)      │   (Logger Bot)  │   (Database)            │
│                 │                 │                         │
│   - OpenAI API  │   - MongoDB     │   - mongo:7             │
│   - Telegram    │   - Telegram    │   - Volume: mongo_data  │
│                 │                 │                         │
└────────┬────────┴────────┬────────┴────────────┬────────────┘
         │                 │                      │
         ▼                 ▼                      │
   ┌──────────┐      ┌──────────┐                │
   │ Telegram │      │ Telegram │                │
   │   API    │      │   API    │                │
   └──────────┘      └──────────┘                │
                           │                      │
                           └──────────────────────┘
                                 (internal network)
```

---

## Quick Reference

### Commands

| Command | Description |
|---------|-------------|
| `docker compose up -d --build` | Build and start all services |
| `docker compose down` | Stop all services |
| `docker compose logs -f` | Follow all logs |
| `docker compose ps` | Show service status |
| `docker compose restart <service>` | Restart a service |

### Bot Commands

**Facto Bot:**
| Command | Description |
|---------|-------------|
| `/code <question>` | Switch to code mode |
| `/general <question>` | Switch to general mode |
| `/journal <diary entry>` | Format diary entry (one-shot, no topic) |
| `/delete` | Delete current topic |

**Logta Bot:**
| Command | Description |
|---------|-------------|
| `/stats` | Show logging statistics (owner only) |

---

## 9. Remote Access with Tailscale

Tailscale provides secure remote access to your deployment without exposing ports to the public internet.

### Prerequisites

- [Tailscale](https://tailscale.com/download) installed on your server
- Server connected to your Tailscale network (`tailscale up`)

### Expose Services via Tailscale

```bash
# 1. Serve the Dashboard UI over HTTPS (Port 443)
sudo tailscale serve --bg --https=443 http://127.0.0.1:3001

# 2. Serve the WebSocket server over HTTPS (Port 8081)
sudo tailscale serve --bg --https=8081 http://127.0.0.1:8081
```

### Accessing the Dashboard

Once configured, access your dashboard at:
```
https://<machine-name>.<tailnet-name>.ts.net
```

The WebSocket will automatically connect to:
```
wss://<machine-name>.<tailnet-name>.ts.net:8081
```

### Important: WebSocket Configuration

> **Do NOT use `--tcp` for the WebSocket port.**

The dashboard serves over HTTPS, so the browser expects a secure WebSocket (`wss://`) connection. Using `--tcp` creates a raw TCP tunnel without TLS termination, causing connection failures.

| Command | Result |
|---------|--------|
| `--https=8081 http://...` | Works - Tailscale terminates TLS |
| `--tcp=8081 tcp://...` | Fails - No TLS, browser expects WSS |

### Managing Tailscale Serve

```bash
# View current serve configuration
tailscale serve status

# Remove a specific serve rule
sudo tailscale serve --https=8081 off
sudo tailscale serve --https=443 off

# Remove all serve rules
sudo tailscale serve reset
```

### Troubleshooting Tailscale

**WebSocket connection fails with "wss://" error:**
- Ensure you're using `--https` not `--tcp` for the WebSocket port
- Verify the serve is active: `tailscale serve status`

**Cannot access dashboard:**
- Check Tailscale is connected: `tailscale status`
- Verify the serve is running: `tailscale serve status`
- Ensure the local service is running on the correct port

---

## Support

For issues and feature requests, please open an issue on the repository.
