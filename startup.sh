#!/bin/bash
# start.sh

# Wait for the PostgreSQL database to be ready
echo "Waiting for PostgreSQL to start..."

# Inside Docker network, the database service is called 'db' and uses the internal port 5432
DB_HOST="db"
DB_PORT="5432"

# Loop until netcat (nc) confirms connectivity to the database host and port
while ! nc -z $DB_HOST $DB_PORT; do
  echo "Database connection failed. Retrying in 1 second..."
  sleep 1
done

echo "PostgreSQL started successfully! Launching FastAPI..."

# IMPORTANT FIX: The module path must be 'app.main:app' because main.py is now inside the 'app' directory.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload