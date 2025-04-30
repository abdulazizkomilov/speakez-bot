#!/bin/bash

# Check Redis (port 6380)
if ! nc -z redis 6380; then
  echo "Redis not reachable"
  exit 1
fi

# Check Kafka port
if ! nc -z kafka 29092; then
  echo "Kafka not reachable"
  exit 1
fi

exit 0
