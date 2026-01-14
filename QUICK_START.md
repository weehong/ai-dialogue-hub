# Quick Start Guide

## Setup (One-time)

### 1. Configure Environment

```bash
# Copy the example file
cp .env.example .env

# Edit with your credentials
nano .env
```

Required variables:
- `FACTO_TOKEN` - Your Facto bot token from @BotFather
- `LOGTA_TOKEN` - Your Logta bot token from @BotFather
- `OPENAI_API_KEY` - Your OpenAI API key
- `OWNER_ID` - Your Telegram user ID

Optional (for Docker Hub):
- `DOCKER_USER` - Your Docker Hub username
- `DOCKER_TOKEN` - Your Docker Hub personal access token
- `IMAGE_TAG` - Tag to use (default: latest)
- `BUILD_PLATFORM` - Build platform (default: native, set to `linux/amd64` for cloud)

### 2. Get Docker Hub Token (Optional)

If you want to publish images:

1. Go to https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Copy the token (starts with `dckr_pat_`)
4. Add to `.env`:
   ```
   DOCKER_TOKEN=dckr_pat_your_token_here
   ```

---

## Development (Local)

### Build and Run Locally

```bash
# Build all images and start services
docker compose up -d --build

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Access Services

- Dashboard: http://localhost:3000
- WebSocket: ws://localhost:8080
- Meilisearch: http://localhost:7700
- MongoDB: localhost:27017

---

## Publishing to Docker Hub

### Method 1: Fully Automated (Recommended)

```bash
# Configure .env with Docker Hub credentials
DOCKER_USER=your_username
DOCKER_TOKEN=dckr_pat_your_token
IMAGE_TAG=latest
BUILD_PLATFORM=linux/amd64

# Run publish script
./publish_docker.sh
```

### Method 2: Interactive

```bash
# Script will prompt for missing values
./publish_docker.sh
```

The script will:
- ✅ Auto-login using your token
- ✅ Build all 5 images
- ✅ Push to Docker Hub

---

## Deployment (Production Server)

### Option A: Using Docker Hub Images

```bash
# 1. Clone repository
git clone <your-repo>
cd facto

# 2. Configure environment
cp .env.example .env
nano .env

# Add your bot tokens and API keys
# Add Docker Hub config:
echo "DOCKER_USER=your_dockerhub_username" >> .env
echo "IMAGE_TAG=latest" >> .env

# 3. Pull pre-built images and start
docker compose pull
docker compose up -d

# 4. Check status
docker compose ps
docker compose logs -f
```

### Option B: Build on Server

```bash
# 1. Clone and configure
git clone <your-repo>
cd facto
cp .env.example .env
nano .env

# 2. Build and start
docker compose up -d --build
```

---

## Updating Deployment

### Update from Docker Hub

```bash
# On your development machine, publish new version
IMAGE_TAG=v1.1.0 ./publish_docker.sh

# On server, pull and restart
export IMAGE_TAG=v1.1.0
docker compose pull
docker compose up -d
```

### Update from Source

```bash
# On server
git pull
docker compose up -d --build
```

---

## Common Commands

### Docker Compose

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs (all)
docker compose logs -f

# View logs (specific service)
docker compose logs -f facto
docker compose logs -f logta
docker compose logs -f dashboard

# Restart a service
docker compose restart facto

# Rebuild a service
docker compose up -d --build facto

# Pull latest images
docker compose pull

# Check service status
docker compose ps
```

### Docker Images

```bash
# List local images
docker images | grep facto

# Remove local images
docker rmi facto-bot:latest
docker rmi logta-bot:latest

# Remove all unused images
docker image prune -a
```

### Troubleshooting

```bash
# Check if services are running
docker compose ps

# Check service health
docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# View real-time logs
docker compose logs -f facto logta

# Restart all services
docker compose restart

# Remove everything and start fresh
docker compose down -v
docker compose up -d --build
```

---

## Service Architecture

```
┌─────────────────────────────────────────────────┐
│                Docker Compose                    │
├──────────┬──────────┬──────────┬──────────┬─────┤
│  facto   │  logta   │dashboard │ dash-ws  │dash-│
│ (AI Bot) │ (Logger) │ (Web UI) │ (Socket) │sync │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴─────┘
     │          │          │          │
     │          ├──────────┴──────────┤
     │          │                     │
     │     ┌────▼────┐          ┌────▼────────┐
     │     │ MongoDB │          │ Meilisearch │
     │     └─────────┘          └─────────────┘
     │
     ▼
┌─────────────┐
│ Telegram    │
│ Bot API     │
└─────────────┘
```

---

## Bot Setup

### 1. Create Bots in Telegram

1. Message @BotFather
2. Create Facto bot: `/newbot`
3. Create Logta bot: `/newbot`
4. Save both tokens

### 2. Disable Group Privacy

For BOTH bots:
1. @BotFather → `/mybots`
2. Select bot → Bot Settings → Group Privacy → Turn off

### 3. Add Bots to Groups

**Facto Bot:**
- Add to a Forum group (with Topics enabled)
- Make admin with "Manage Topics" and "Delete Messages"

**Logta Bot:**
- Add to any group you want to log
- Messages are logged automatically

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FACTO_TOKEN` | Yes | - | Facto bot token |
| `LOGTA_TOKEN` | Yes | - | Logta bot token |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `OWNER_ID` | Yes | - | Your Telegram user ID |
| `MONGODB_URI` | No | mongodb://mongodb:27017 | MongoDB connection |
| `MEILISEARCH_API_KEY` | No | masterKey | Meilisearch key |
| `DOCKER_USER` | No | - | Docker Hub username |
| `DOCKER_TOKEN` | No | - | Docker Hub token |
| `IMAGE_TAG` | No | latest | Docker image tag |
| `BUILD_PLATFORM` | No | native | Build platform |

---

## Need Help?

- Check logs: `docker compose logs -f`
- Verify env: `cat .env`
- Test MongoDB: `docker compose exec mongodb mongosh`
- Restart services: `docker compose restart`
- Full docs: See `DEPLOYMENT.md` and `DOCKER_HUB.md`
