#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "🐳 Facto Bot Suite - Docker Publisher"
echo "======================================"

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading configuration from .env file..."
    # Export variables from .env, ignoring comments and empty lines
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
else
    echo "Warning: .env file not found"
fi

# Check if docker is accessible
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running or you don't have permission."
    echo "Please start Docker or run 'docker login' if needed."
    exit 1
fi

# 1. Get DockerHub Username (from .env or prompt)
if [ -z "$DOCKER_USER" ]; then
    read -p "Enter your DockerHub Username: " DOCKER_USER
fi

if [ -z "$DOCKER_USER" ]; then
    echo "Error: Docker Hub username is required."
    echo "Set DOCKER_USER in .env file or enter it when prompted."
    exit 1
fi

echo "Docker Hub User: $DOCKER_USER"

# 2. Login to Docker Hub if token is provided
if [ -n "$DOCKER_TOKEN" ]; then
    echo "Logging in to Docker Hub..."
    echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USER" --password-stdin
    if [ $? -eq 0 ]; then
        echo "✅ Successfully logged in to Docker Hub"
    else
        echo "Error: Failed to login to Docker Hub"
        exit 1
    fi
else
    echo "No DOCKER_TOKEN found in .env file."
    echo "Checking if already logged in..."
    if ! docker info | grep -q "Username: $DOCKER_USER"; then
        echo "Please login to Docker Hub manually:"
        docker login
    fi
fi

# 3. Get Tag (from .env or prompt)
if [ -z "$IMAGE_TAG" ]; then
    read -p "Enter Tag (default: latest): " IMAGE_TAG
fi
IMAGE_TAG=${IMAGE_TAG:-latest}

# 4. Platform selection (from .env or prompt)
if [ -z "$BUILD_PLATFORM" ]; then
    read -p "Build for linux/amd64 platform? (recommended for cloud servers) (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BUILD_PLATFORM="linux/amd64"
    fi
fi

if [ -n "$BUILD_PLATFORM" ]; then
    PLATFORM_FLAG="--platform $BUILD_PLATFORM"
    echo "Building for platform: $BUILD_PLATFORM"
else
    PLATFORM_FLAG=""
    echo "Building for native platform"
fi

echo ""
echo "================================================"
echo "Will build and push the following images:"
echo "  - $DOCKER_USER/facto-bot:$IMAGE_TAG"
echo "  - $DOCKER_USER/logta-bot:$IMAGE_TAG"
echo "  - $DOCKER_USER/worklog-bot:$IMAGE_TAG"
echo "  - $DOCKER_USER/facto-dashboard:$IMAGE_TAG"
echo "  - $DOCKER_USER/facto-dashboard-ws:$IMAGE_TAG"
echo "  - $DOCKER_USER/facto-dashboard-sync:$IMAGE_TAG"
echo "================================================"
echo ""

# Confirm before proceeding
read -p "Ready to build and push all images? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "🔨 Building images..."
echo ""

# Build Facto Bot
echo "[1/6] Building facto-bot..."
docker build $PLATFORM_FLAG -t "$DOCKER_USER/facto-bot:$IMAGE_TAG" ./src/facto
echo "✅ facto-bot built"
echo ""

# Build Logta Bot
echo "[2/6] Building logta-bot..."
docker build $PLATFORM_FLAG -t "$DOCKER_USER/logta-bot:$IMAGE_TAG" ./src/logta
echo "✅ logta-bot built"
echo ""

# Build WorkLog Bot
echo "[3/6] Building worklog-bot..."
docker build $PLATFORM_FLAG -t "$DOCKER_USER/worklog-bot:$IMAGE_TAG" ./src/worklog
echo "✅ worklog-bot built"
echo ""

# Build Dashboard (runner)
echo "[4/6] Building facto-dashboard (web UI)..."
docker build $PLATFORM_FLAG -t "$DOCKER_USER/facto-dashboard:$IMAGE_TAG" --target runner ./src/dashboard
echo "✅ facto-dashboard built"
echo ""

# Build Dashboard WebSocket
echo "[5/6] Building facto-dashboard-ws (websocket server)..."
docker build $PLATFORM_FLAG -t "$DOCKER_USER/facto-dashboard-ws:$IMAGE_TAG" --target websocket ./src/dashboard
echo "✅ facto-dashboard-ws built"
echo ""

# Build Dashboard Sync
echo "[6/6] Building facto-dashboard-sync (meilisearch sync)..."
docker build $PLATFORM_FLAG -t "$DOCKER_USER/facto-dashboard-sync:$IMAGE_TAG" --target sync ./src/dashboard
echo "✅ facto-dashboard-sync built"
echo ""

# Push all images
echo "🚀 Pushing images to DockerHub..."
echo ""

docker push "$DOCKER_USER/facto-bot:$IMAGE_TAG"
echo "✅ Pushed facto-bot"

docker push "$DOCKER_USER/logta-bot:$IMAGE_TAG"
echo "✅ Pushed logta-bot"

docker push "$DOCKER_USER/worklog-bot:$IMAGE_TAG"
echo "✅ Pushed worklog-bot"

docker push "$DOCKER_USER/facto-dashboard:$IMAGE_TAG"
echo "✅ Pushed facto-dashboard"

docker push "$DOCKER_USER/facto-dashboard-ws:$IMAGE_TAG"
echo "✅ Pushed facto-dashboard-ws"

docker push "$DOCKER_USER/facto-dashboard-sync:$IMAGE_TAG"
echo "✅ Pushed facto-dashboard-sync"

echo ""
echo "================================================"
echo "✅ Success! All images published to DockerHub"
echo "================================================"
echo ""
echo "To use these images, update your compose.yml with:"
echo "DOCKER_USER=$DOCKER_USER IMAGE_TAG=$IMAGE_TAG"
echo ""
echo "Then run: docker compose pull && docker compose up -d"
