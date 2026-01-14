# Docker Hub Publishing Guide

This guide explains how to publish and use Docker images from Docker Hub.

## Publishing to Docker Hub

### Prerequisites

1. Create a Docker Hub account at https://hub.docker.com
2. Create a Personal Access Token:
   - Go to https://hub.docker.com/settings/security
   - Click "New Access Token"
   - Give it a description (e.g., "Facto Bot Publishing")
   - Copy the token (starts with `dckr_pat_`)

### Setup Credentials

Add your Docker Hub credentials to `.env`:

```bash
# Add to your .env file
DOCKER_USER=your_dockerhub_username
DOCKER_TOKEN=dckr_pat_your_token_here
IMAGE_TAG=latest
BUILD_PLATFORM=linux/amd64  # Optional: for cloud servers
```

### Publish All Images

Run the publish script:

```bash
chmod +x publish_docker.sh
./publish_docker.sh
```

The script will:
1. Load credentials from `.env` file (or prompt if missing)
2. Automatically login to Docker Hub using your token
3. Use the image tag from `.env` (or prompt if missing)
4. Use the build platform from `.env` (or prompt if missing)
5. Build all 5 images
6. Push them to Docker Hub

### Manual Publishing (without .env)

If you prefer to enter credentials manually:

```bash
# The script will prompt for missing values
./publish_docker.sh
```

### Published Images

The script publishes these images:
- `{username}/facto-bot:{tag}` - AI Consultant Bot
- `{username}/logta-bot:{tag}` - Message Logger Bot
- `{username}/facto-dashboard:{tag}` - Dashboard Web UI
- `{username}/facto-dashboard-ws:{tag}` - WebSocket Server
- `{username}/facto-dashboard-sync:{tag}` - Meilisearch Sync Service

---

## Using Pre-built Images

### Option 1: Pull and Use Docker Hub Images

Set environment variables and pull images:

```bash
export DOCKER_USER=your_dockerhub_username
export IMAGE_TAG=latest

# Pull all images
docker compose pull

# Start services (without rebuilding)
docker compose up -d
```

### Option 2: Use .env File

Create or update your `.env` file:

```bash
# Add these to your .env file
DOCKER_USER=your_dockerhub_username
IMAGE_TAG=latest
```

Then run:

```bash
docker compose pull
docker compose up -d
```

### Option 3: Build Locally (Default)

If you don't set `DOCKER_USER`, it will build images locally:

```bash
# This will build all images locally
docker compose up -d --build
```

---

## Deployment to Cloud Server

### 1. On Your Cloud Server

```bash
# Clone the repository
git clone <your-repo-url>
cd facto

# Create .env file with your credentials
cp .env.example .env
nano .env  # Edit with your tokens and API keys

# Add Docker Hub configuration
echo "DOCKER_USER=your_dockerhub_username" >> .env
echo "IMAGE_TAG=latest" >> .env

# Pull images from Docker Hub
docker compose pull

# Start all services
docker compose up -d

# View logs
docker compose logs -f
```

### 2. Update Deployment

When you push new images to Docker Hub:

```bash
# On your server
docker compose pull
docker compose up -d
```

---

## Image Tags Strategy

### Using Versions

Instead of `latest`, you can use version tags:

```bash
./publish_docker.sh
# Enter tag: v1.0.0
```

Deploy specific version:
```bash
export IMAGE_TAG=v1.0.0
docker compose pull
docker compose up -d
```

### Recommended Tagging

- `latest` - Latest stable release
- `v1.0.0` - Specific version
- `dev` - Development builds
- `staging` - Staging builds

---

## Troubleshooting

### Authentication Error

If you get authentication errors:

1. **Using the script**: Make sure `DOCKER_TOKEN` is set correctly in `.env`
   ```bash
   # Check your .env file
   grep DOCKER_TOKEN .env
   ```

2. **Manual login**: Use your Personal Access Token as password
   ```bash
   docker login -u your_username
   # When prompted for password, paste your token (dckr_pat_...)
   ```

3. **Verify token**: Make sure token has "Read, Write, Delete" permissions

### Image Not Found

Make sure you've published the images:

```bash
# Check if images exist on Docker Hub
docker search your_username/facto-bot
```

### Wrong Architecture

If running on ARM-based cloud (rare), rebuild without platform flag:
- Edit `publish_docker.sh`
- Remove or modify the `PLATFORM_FLAG` when prompted

### Force Rebuild

To force rebuild instead of using cached images:

```bash
docker compose build --no-cache
docker compose up -d
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Publish Docker Images

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and Push
        env:
          DOCKER_USER: ${{ secrets.DOCKER_USERNAME }}
          IMAGE_TAG: ${{ github.ref_name }}
        run: |
          docker build -t $DOCKER_USER/facto-bot:$IMAGE_TAG ./src/facto
          docker build -t $DOCKER_USER/logta-bot:$IMAGE_TAG ./src/logta
          docker build -t $DOCKER_USER/facto-dashboard:$IMAGE_TAG --target runner ./src/dashboard
          docker build -t $DOCKER_USER/facto-dashboard-ws:$IMAGE_TAG --target websocket ./src/dashboard
          docker build -t $DOCKER_USER/facto-dashboard-sync:$IMAGE_TAG --target sync ./src/dashboard
          docker push $DOCKER_USER/facto-bot:$IMAGE_TAG
          docker push $DOCKER_USER/logta-bot:$IMAGE_TAG
          docker push $DOCKER_USER/facto-dashboard:$IMAGE_TAG
          docker push $DOCKER_USER/facto-dashboard-ws:$IMAGE_TAG
          docker push $DOCKER_USER/facto-dashboard-sync:$IMAGE_TAG
```

---

## Image Size Optimization

Current image sizes:
- facto-bot: ~274MB
- logta-bot: ~260MB
- facto-dashboard: ~297MB
- facto-dashboard-ws: ~1.02GB
- facto-dashboard-sync: ~1.02GB

To reduce size further:
1. Use multi-stage builds (already implemented)
2. Remove development dependencies
3. Use alpine base images (already implemented for Node.js)
4. Minimize layer count
