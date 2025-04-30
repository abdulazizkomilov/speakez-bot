#!/bin/bash

# === Wait for Redis ===
echo "Waiting for Redis on redis:6380..."
while ! nc -z redis 6380; do
  echo "Redis is not available yet. Waiting..."
  sleep 3
done
echo "✅ Redis is up!"

# === Wait for MongoDB ===
echo "Waiting for MongoDB port..."
while ! nc -z mongo 27017; do
  echo "MongoDB port not open yet. Waiting..."
  sleep 2
done
echo "✅ MongoDB is up!"

echo "Starting celery..."

celery -A utils.celery.celery_app worker --loglevel=info --concurrency=4

echo "Stopped celery..."
