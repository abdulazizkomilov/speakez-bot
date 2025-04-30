#!/bin/bash

# === Wait for Kafka DNS and port ===
echo "Waiting for Kafka service (DNS)..."
until getent hosts kafka > /dev/null; do
  echo "Waiting for kafka DNS to resolve..."
  sleep 2
done

echo "Waiting for Kafka on kafka:29092..."
while ! nc -z kafka 29092; do
  echo "Kafka is not available yet. Waiting..."
  sleep 3
done
echo "✅ Kafka is up!"

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

# === Start the Bot ===
echo "🚀 Starting bot..."
exec python app.py
