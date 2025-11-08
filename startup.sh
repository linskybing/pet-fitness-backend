#!/bin/bash
# start.sh

echo "Starting FastAPI application..."

# Use PORT environment variable from Cloud Run, default to 8080 for local development
PORT=${PORT:-8080}

echo "Container will listen on port: $PORT"

# Launch FastAPI without --reload for production (Cloud Run)
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT