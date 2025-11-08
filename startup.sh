#!/bin/bash
# start.sh

echo "Starting FastAPI application..."

# Launch FastAPI with the correct module path
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload