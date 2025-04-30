#!/bin/bash

set -e
set -o pipefail

if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "❌ .env file not found!"
  exit 1
fi

if [[ -z "$DOCKER_USER" || -z "$BOT_IMAGE" || -z "$MAIN_IMAGE" || -z "$CELERY_IMAGE" || -z "$TAG" ]]; then
  echo "❌ Missing required variables in .env (DOCKER_USER, BOT_IMAGE, etc.)"
  exit 1
fi

echo "🔧 Using tag: $TAG"

### === BOT IMAGE ===
echo "📦 Building bot image..."
docker build -t "$DOCKER_USER/$BOT_IMAGE:$TAG" -f Dockerfile .

echo "🚀 Pushing bot image..."
docker push "$DOCKER_USER/$BOT_IMAGE:$TAG"

echo "🧹 Removing local bot image..."
docker rmi "$DOCKER_USER/$BOT_IMAGE:$TAG" || true


### === MAIN IMAGE ===
echo "📦 Building main image..."
docker build -t "$DOCKER_USER/$MAIN_IMAGE:$TAG" -f Dockerfile-main .

echo "🚀 Pushing main image..."
docker push "$DOCKER_USER/$MAIN_IMAGE:$TAG"

echo "🧹 Removing local main image..."
docker rmi "$DOCKER_USER/$MAIN_IMAGE:$TAG" || true


### === CELERY IMAGE ===
echo "📦 Building celery image..."
docker build -t "$DOCKER_USER/$CELERY_IMAGE:$TAG" -f Dockerfile-celery .

echo "🚀 Pushing celery image..."
docker push "$DOCKER_USER/$CELERY_IMAGE:$TAG"

echo "🧹 Removing local celery image..."
docker rmi "$DOCKER_USER/$CELERY_IMAGE:$TAG" || true

echo "✅ All images built, pushed, and cleaned up."

echo "🧹 Running full Docker cleanup..."
docker system prune -f
